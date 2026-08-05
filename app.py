import json
import secrets
import time
from collections import defaultdict

from flask import Flask, render_template, request, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os

load_dotenv()

from backend.auth import login_required, admin_required
from backend.routes.network import network_bp
from backend.routes.routing import routing_bp
from backend.routes.traffic import traffic_bp
from backend.routes.scenarios import scenarios_bp
from backend.routes.admin import admin_bp
from backend.models.database import get_db, init_db
from backend.services import traffic_service

# Demo credentials — passwords are hashed, never stored or compared in plaintext.
# Override via env vars to change the logins without touching source. Two demo
# accounts are seeded so the login page can show one of each role.
DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo")
DEMO_PASSWORD_HASH = os.getenv("DEMO_PASSWORD_HASH") or generate_password_hash(
    os.getenv("DEMO_PASSWORD", "urbanflow"), method="pbkdf2:sha256"
)

DEMO_PLANNER_USERNAME = os.getenv("DEMO_PLANNER_USERNAME", "planner")
DEMO_PLANNER_PASSWORD_HASH = os.getenv("DEMO_PLANNER_PASSWORD_HASH") or generate_password_hash(
    os.getenv("DEMO_PLANNER_PASSWORD", "planner123"), method="pbkdf2:sha256"
)

# Simple in-memory login rate limit: max 5 attempts per IP per LOGIN_WINDOW_SECONDS.
# Good enough to blunt naive brute-forcing of the demo credentials; not a
# substitute for a real rate-limiting layer (e.g. flask-limiter + Redis) in production.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60
_login_attempts = defaultdict(list)


def _login_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < LOGIN_WINDOW_SECONDS]
    _login_attempts[ip] = attempts
    return len(attempts) >= LOGIN_MAX_ATTEMPTS


def _record_login_attempt(ip: str) -> None:
    _login_attempts[ip].append(time.time())


def _seed_demo_users(app) -> None:
    """First run only: create the two demo accounts (one per role)."""
    db = get_db(app)
    count = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    if count == 0:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (DEMO_USERNAME, DEMO_PASSWORD_HASH, "admin"),
        )
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (DEMO_PLANNER_USERNAME, DEMO_PLANNER_PASSWORD_HASH, "planner"),
        )
        db.commit()
    db.close()


def _seed_traffic_profile(app) -> None:
    """Seed traffic_profiles from the hardcoded defaults on first run, then
    sync the in-memory prediction model with whatever is currently in the DB
    (picks up admin-saved calibration after a restart)."""
    db = get_db(app)
    count = db.execute("SELECT COUNT(*) AS n FROM traffic_profiles").fetchone()["n"]
    if count == 0:
        for highway_type, values in traffic_service.get_default_profile().items():
            db.execute(
                "INSERT INTO traffic_profiles (highway_type, profile_json) VALUES (?,?)",
                (highway_type, json.dumps(values)),
            )
        db.commit()
    rows = db.execute("SELECT highway_type, profile_json FROM traffic_profiles").fetchall()
    db.close()
    traffic_service.set_profile({r["highway_type"]: json.loads(r["profile_json"]) for r in rows})


def create_app(database=None):
    """
    database: optional path override for the SQLite file, used by the test
    suite to point each test at an isolated database instead of the real one.
    """
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static"
    )

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        if os.getenv("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY must be set in the environment for production.")
        # Dev-only fallback: random per-run key, never a fixed string checked into source.
        secret_key = secrets.token_hex(32)
    app.config["SECRET_KEY"] = secret_key
    app.config["DATABASE"] = database or os.path.join(app.instance_path, "urbanflow.db")

    # Restrict CORS to the app's own origin(s) rather than allowing any origin.
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5050,http://127.0.0.1:5050"
    ).split(",")
    CORS(app, origins=allowed_origins)

    app.register_blueprint(network_bp,   url_prefix="/api/network")
    app.register_blueprint(routing_bp,   url_prefix="/api/routing")
    app.register_blueprint(traffic_bp,   url_prefix="/api/traffic")
    app.register_blueprint(scenarios_bp, url_prefix="/api/scenarios")
    app.register_blueprint(admin_bp,     url_prefix="/api/admin")

    @app.route("/")
    def landing():
        return render_template("landing.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            ip = request.remote_addr or "unknown"
            if _login_rate_limited(ip):
                error = "Too many login attempts. Please wait a minute and try again."
                return render_template("login.html", error=error), 429

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            db = get_db(app)
            row = db.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            db.close()
            if row and check_password_hash(row["password_hash"], password):
                session["logged_in"] = True
                session["username"] = row["username"]
                session["role"] = row["role"]
                session["user_id"] = row["id"]
                return redirect(url_for("app_index"))
            _record_login_attempt(ip)
            error = "Incorrect username or password. Try the demo credentials below."
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("landing"))

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/app")
    @login_required
    def app_index():
        return render_template("index.html", role=session.get("role"))

    @app.route("/admin")
    @admin_required
    def admin_page():
        return render_template("admin.html")

    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        init_db(app)
        _seed_demo_users(app)
        _seed_traffic_profile(app)

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5050))
    debug = os.getenv("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
