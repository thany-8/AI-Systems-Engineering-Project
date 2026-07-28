"""Core recommendation + health API.

Defined as a module-level blueprint (not inside the app factory) so its rate
limit is registered exactly once, not re-registered on every ``create_app`` call.
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from app import config, guardrails, pipeline
from app.extensions import limiter

bp = Blueprint("api", __name__)


@bp.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "mode": config.llm_mode(),
            "model": config.GEMINI_MODEL if config.USE_LLM else None,
        }
    )


@bp.post("/api/recommend")
@limiter.limit(lambda: current_app.config["RATELIMIT_RECOMMEND"])
def recommend():
    from app.feedback import profile_for

    data = request.get_json(silent=True) or {}
    # Personalize from the signed-in user's history (reactions + saved playlists).
    profile = profile_for(current_user) if current_user.is_authenticated else None
    try:
        result = pipeline.recommend(
            data.get("query", ""),
            user_profile=profile,
            intensity=data.get("intensity"),
        )
    except guardrails.GuardrailError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # pragma: no cover - defensive
        current_app.logger.exception("recommend request failed")
        return jsonify({"error": "internal error"}), 500
    return jsonify(result)
