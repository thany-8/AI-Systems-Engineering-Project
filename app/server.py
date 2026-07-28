"""Flask backend for the AI Playlist Generator.

Pages (served from ``static/``):
  * ``GET /``        → landing page + playlist generator
  * ``GET /login``   → login page
  * ``GET /signup``  → create-account page
  * ``GET /library`` → saved playlists (requires an account)

JSON API:
  * ``GET  /api/health``    → reasoning mode (gemini/offline)
  * ``POST /api/recommend`` → run the RAG pipeline: {"query": "..."}
  * ``/api/auth/*``         → signup / login / logout / me
  * ``/api/playlists*``     → list / create / delete saved playlists
"""
from __future__ import annotations

from flask import Flask, jsonify, send_from_directory
from sqlalchemy.exc import OperationalError

from app import config
from app.extensions import db, limiter, login_manager


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(
        SECRET_KEY=config.SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=config.DATABASE_URL,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        RATELIMIT_STORAGE_URI=config.RATELIMIT_STORAGE_URI,
        RATELIMIT_ENABLED=config.RATELIMIT_ENABLED,
        RATELIMIT_HEADERS_ENABLED=True,
        RATELIMIT_RECOMMEND=config.RATELIMIT_RECOMMEND,
        RATELIMIT_AUTH=config.RATELIMIT_AUTH,
    )
    if test_config:
        app.config.update(test_config)
    # Rate limiting is off during tests unless a test explicitly enables it.
    if app.config.get("TESTING") and (test_config or {}).get("RATELIMIT_ENABLED") is None:
        app.config["RATELIMIT_ENABLED"] = False

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    @login_manager.unauthorized_handler
    def _unauthorized():
        return jsonify({"error": "Please log in to continue."}), 401

    @app.errorhandler(429)
    def _rate_limited(exc):
        return jsonify({"error": "Too many requests — please slow down and try again shortly."}), 429

    # Import models so their tables register, then register the API blueprints.
    from app import models  # noqa: F401  (side effect: model + user_loader setup)
    from app.api import bp as api_bp
    from app.auth import bp as auth_bp
    from app.playlists import bp as playlists_bp
    from app.feedback import bp as feedback_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(playlists_bp)
    app.register_blueprint(feedback_bp)

    with app.app_context():
        # ``checkfirst`` avoids recreating existing tables; the try/except also
        # tolerates the rare first-boot race when multiple workers run without
        # ``preload_app`` (another worker created the tables concurrently).
        try:
            db.create_all()
        except OperationalError:  # pragma: no cover - concurrent first boot
            app.logger.warning("db.create_all() race ignored (tables already exist)")

    def _page(name: str):
        return send_from_directory(app.static_folder, name)

    @app.get("/")
    def index():
        return _page("index.html")

    @app.get("/login")
    def login_page():
        return _page("login.html")

    @app.get("/signup")
    def signup_page():
        return _page("signup.html")

    @app.get("/library")
    def library_page():
        return _page("library.html")

    return app


app = create_app()
