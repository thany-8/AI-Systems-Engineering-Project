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

from flask import Flask, jsonify, request, send_from_directory

from app import config, guardrails, pipeline
from app.extensions import db, login_manager


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(
        SECRET_KEY=config.SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=config.DATABASE_URL,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def _unauthorized():
        return jsonify({"error": "Please log in to continue."}), 401

    # Import models so their tables register, then register the API blueprints.
    from app import models  # noqa: F401  (side effect: model + user_loader setup)
    from app.auth import bp as auth_bp
    from app.playlists import bp as playlists_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(playlists_bp)

    with app.app_context():
        db.create_all()

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

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "mode": config.llm_mode(),
                "model": config.GEMINI_MODEL if config.USE_LLM else None,
            }
        )

    @app.post("/api/recommend")
    def recommend():
        data = request.get_json(silent=True) or {}
        try:
            result = pipeline.recommend(data.get("query", ""))
        except guardrails.GuardrailError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:  # pragma: no cover - defensive
            app.logger.exception("recommend request failed")
            return jsonify({"error": "internal error"}), 500
        return jsonify(result)

    return app


app = create_app()
