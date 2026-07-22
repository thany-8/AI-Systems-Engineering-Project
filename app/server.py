"""Flask backend for PawPal+ Companion.

Serves the static chat UI and exposes the agent over a small JSON API:
* ``GET  /``            → the chat page
* ``GET  /api/health``  → reasoning mode (gemini/offline)
* ``POST /api/chat``    → run one agent turn: {"message": "..."}
"""
from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory

from app import agent, config, guardrails


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

    @app.post("/api/chat")
    def chat():
        data = request.get_json(silent=True) or {}
        try:
            result = agent.run(data.get("message", ""))
        except guardrails.GuardrailError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:  # pragma: no cover - defensive
            app.logger.exception("chat request failed")
            return jsonify({"error": "internal error"}), 500
        return jsonify(result)

    return app


app = create_app()
