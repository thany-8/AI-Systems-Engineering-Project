"""Flask backend for the Music RAG Recommender.

* ``GET  /``             → the chat UI
* ``GET  /api/health``   → reasoning mode (gemini/offline)
* ``POST /api/recommend``→ run the RAG pipeline: {"query": "..."}
"""
from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory

from app import config, guardrails, pipeline


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

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
