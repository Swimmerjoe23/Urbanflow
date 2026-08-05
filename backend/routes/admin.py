import json
import logging
import sqlite3

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.security import generate_password_hash

from backend.auth import admin_required
from backend.models.database import get_db
from backend.services import traffic_service

admin_bp = Blueprint("admin", __name__)
logger = logging.getLogger(__name__)

USERNAME_MAX_LEN = 50
PASSWORD_MIN_LEN = 8
ROLES = ("admin", "planner")


def _validate_username(username):
    if not username:
        return "username is required"
    if len(username) > USERNAME_MAX_LEN:
        return f"username must be at most {USERNAME_MAX_LEN} characters"
    return None


def _validate_password(password):
    if not password or len(password) < PASSWORD_MIN_LEN:
        return f"password must be at least {PASSWORD_MIN_LEN} characters"
    return None


def _validate_role(role):
    if role not in ROLES:
        return f"role must be one of {ROLES}"
    return None


def _admin_count(db):
    return db.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'").fetchone()["n"]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """GET /api/admin/users — list all accounts (never returns password_hash)."""
    db = get_db(current_app)
    rows = db.execute(
        "SELECT id, username, role, created_at FROM users ORDER BY created_at"
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    """POST /api/admin/users — Body: { username, password, role }"""
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    role = body.get("role") or "planner"

    err = _validate_username(username) or _validate_password(password) or _validate_role(role)
    if err:
        return jsonify({"error": err}), 400

    db = get_db(current_app)
    try:
        cur = db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (username, generate_password_hash(password, method="pbkdf2:sha256"), role),
        )
        db.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({"error": f'A user named "{username}" already exists'}), 409
    except Exception:
        db.close()
        logger.exception("Failed to create user %r", username)
        return jsonify({"error": "Failed to create the user."}), 500
    db.close()
    return jsonify({"id": user_id, "username": username, "role": role}), 201


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    """PUT /api/admin/users/<id> — Body: { role? , password? }"""
    body = request.get_json(silent=True) or {}
    if "role" not in body and "password" not in body:
        return jsonify({"error": "nothing to update — provide role and/or password"}), 400

    db = get_db(current_app)
    row = db.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "User not found"}), 404

    fields, values = [], []

    if "role" in body:
        role = body.get("role")
        err = _validate_role(role)
        if err:
            db.close()
            return jsonify({"error": err}), 400
        if row["role"] == "admin" and role != "admin" and _admin_count(db) <= 1:
            db.close()
            return jsonify({"error": "Cannot demote the last remaining admin"}), 400
        fields.append("role = ?")
        values.append(role)

    if "password" in body:
        password = body.get("password") or ""
        err = _validate_password(password)
        if err:
            db.close()
            return jsonify({"error": err}), 400
        fields.append("password_hash = ?")
        values.append(generate_password_hash(password, method="pbkdf2:sha256"))

    values.append(user_id)
    db.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
    db.commit()
    db.close()
    return jsonify({"id": user_id, "updated": True})


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """DELETE /api/admin/users/<id>"""
    if session.get("user_id") == user_id:
        return jsonify({"error": "Cannot delete your own account"}), 400

    db = get_db(current_app)
    row = db.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "User not found"}), 404
    if row["role"] == "admin" and _admin_count(db) <= 1:
        db.close()
        return jsonify({"error": "Cannot delete the last remaining admin"}), 400

    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    db.close()
    return jsonify({"deleted": user_id})


# ---------------------------------------------------------------------------
# Traffic model calibration
# ---------------------------------------------------------------------------

def _load_profile(db):
    rows = db.execute("SELECT highway_type, profile_json FROM traffic_profiles").fetchall()
    return {r["highway_type"]: json.loads(r["profile_json"]) for r in rows}


def _validate_profile_values(values):
    if not isinstance(values, list) or len(values) != 24:
        return "each profile must be an array of exactly 24 numbers"
    for v in values:
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0 <= v <= 1):
            return "each hourly value must be a number between 0 and 1"
    return None


@admin_bp.route("/traffic-profile", methods=["GET"])
@admin_required
def get_traffic_profile():
    """GET /api/admin/traffic-profile — current per-highway-type hourly congestion baseline."""
    db = get_db(current_app)
    profile = _load_profile(db)
    db.close()
    return jsonify(profile)


@admin_bp.route("/traffic-profile", methods=["PUT"])
@admin_required
def update_traffic_profile():
    """PUT /api/admin/traffic-profile — Body: { highway_type: [24 floats], ... }"""
    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"error": "no highway types provided"}), 400

    for highway_type, values in body.items():
        if highway_type not in traffic_service.HIGHWAY_TYPES:
            return jsonify({"error": f"unknown highway type: {highway_type}"}), 400
        err = _validate_profile_values(values)
        if err:
            return jsonify({"error": f"{highway_type}: {err}"}), 400

    db = get_db(current_app)
    for highway_type, values in body.items():
        db.execute(
            "UPDATE traffic_profiles SET profile_json = ? WHERE highway_type = ?",
            (json.dumps(values), highway_type),
        )
    db.commit()
    profile = _load_profile(db)
    db.close()

    traffic_service.set_profile(profile)
    return jsonify(profile)


@admin_bp.route("/traffic-profile/reset", methods=["POST"])
@admin_required
def reset_traffic_profile():
    """POST /api/admin/traffic-profile/reset — restore the hardcoded default profile."""
    defaults = traffic_service.get_default_profile()

    db = get_db(current_app)
    for highway_type, values in defaults.items():
        db.execute(
            "UPDATE traffic_profiles SET profile_json = ? WHERE highway_type = ?",
            (json.dumps(values), highway_type),
        )
    db.commit()
    profile = _load_profile(db)
    db.close()

    traffic_service.set_profile(profile)
    return jsonify(profile)
