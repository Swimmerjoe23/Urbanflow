import re
import sqlite3

from flask import Blueprint, request, jsonify, current_app
from backend.models.database import get_db
import json

scenarios_bp = Blueprint("scenarios", __name__)

NAME_MAX_LEN = 60
DESCRIPTION_MAX_LEN = 300
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-']*$")


def _validate_name(name):
    if not name:
        return "name is required"
    if len(name) > NAME_MAX_LEN:
        return f"name must be at most {NAME_MAX_LEN} characters"
    if not NAME_RE.match(name):
        return "name may only contain letters, numbers, spaces, hyphens, underscores and apostrophes"
    return None


def _validate_description(description):
    if description and len(description) > DESCRIPTION_MAX_LEN:
        return f"description must be at most {DESCRIPTION_MAX_LEN} characters"
    return None


def _validate_bbox(bbox):
    if bbox is None:
        return None  # optional
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return "bbox must be an array of [south, west, north, east]"
    try:
        south, west, north, east = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return "bbox values must be numeric"
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        return "bbox latitude must be between -90 and 90"
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        return "bbox longitude must be between -180 and 180"
    if south >= north:
        return "bbox south must be less than north"
    if west >= east:
        return "bbox west must be less than east"
    return None


@scenarios_bp.route("/", methods=["GET"])
def list_scenarios():
    """GET /api/scenarios/ — list all saved scenarios."""
    db = get_db(current_app)
    rows = db.execute(
        "SELECT id, name, description, bbox, created_at FROM scenarios ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@scenarios_bp.route("/", methods=["POST"])
def create_scenario():
    """
    POST /api/scenarios/
    Body: { name, description?, bbox, graph_data }
    """
    body = request.get_json(silent=True) or {}
    name        = body.get("name", "").strip()
    description = (body.get("description") or "").strip()
    bbox        = body.get("bbox")
    graph_data  = body.get("graph_data")

    err = _validate_name(name) or _validate_description(description) or _validate_bbox(bbox)
    if err:
        return jsonify({"error": err}), 400
    if not graph_data:
        return jsonify({"error": "graph_data is required"}), 400

    db = get_db(current_app)
    try:
        cur = db.execute(
            "INSERT INTO scenarios (name, description, bbox, graph_data) VALUES (?,?,?,?)",
            (name, description, json.dumps(bbox), json.dumps(graph_data)),
        )
        db.commit()
        scenario_id = cur.lastrowid
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({"error": f'A scenario named "{name}" already exists'}), 409
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 500
    db.close()
    return jsonify({"id": scenario_id, "name": name}), 201


@scenarios_bp.route("/<int:scenario_id>", methods=["GET"])
def get_scenario(scenario_id):
    """GET /api/scenarios/<id> — retrieve a scenario with its graph data."""
    db = get_db(current_app)
    row = db.execute(
        "SELECT * FROM scenarios WHERE id = ?", (scenario_id,)
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Scenario not found"}), 404
    result = dict(row)
    result["graph_data"] = json.loads(result["graph_data"])
    result["bbox"]       = json.loads(result["bbox"]) if result["bbox"] else None
    return jsonify(result)


@scenarios_bp.route("/<int:scenario_id>", methods=["PUT"])
def update_scenario(scenario_id):
    """
    PUT /api/scenarios/<id> — rename or update the description of a scenario.
    Body: { name?, description? }
    """
    body = request.get_json(silent=True) or {}
    if "name" not in body and "description" not in body:
        return jsonify({"error": "nothing to update — provide name and/or description"}), 400

    db = get_db(current_app)
    row = db.execute("SELECT id FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Scenario not found"}), 404

    fields, values = [], []

    if "name" in body:
        name = (body.get("name") or "").strip()
        err = _validate_name(name)
        if err:
            db.close()
            return jsonify({"error": err}), 400
        fields.append("name = ?")
        values.append(name)

    if "description" in body:
        description = (body.get("description") or "").strip()
        err = _validate_description(description)
        if err:
            db.close()
            return jsonify({"error": err}), 400
        fields.append("description = ?")
        values.append(description)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(scenario_id)

    try:
        db.execute(f"UPDATE scenarios SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({"error": f'A scenario named "{body.get("name")}" already exists'}), 409
    db.close()
    return jsonify({"id": scenario_id, "updated": True})


@scenarios_bp.route("/<int:scenario_id>", methods=["DELETE"])
def delete_scenario(scenario_id):
    """DELETE /api/scenarios/<id>"""
    db = get_db(current_app)
    db.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
    db.commit()
    db.close()
    return jsonify({"deleted": scenario_id})
