"""Feedback + taste-profile API.

* ``POST /api/feedback``  — react to a song (👍 / 👎). Sending the same signal
  again clears it (toggle); the opposite signal flips it.
* ``GET  /api/feedback``  — the current user's reactions, so the UI can restore
  button state on a fresh set of results.
* ``GET  /api/profile``   — an aggregated taste profile for display.
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import personalize
from app.extensions import db
from app.models import Feedback

bp = Blueprint("feedback", __name__)

VALID_SIGNALS = {1, -1}


def _num(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


@bp.post("/api/feedback")
@login_required
def add_feedback():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    artist = (data.get("artist") or "").strip()
    try:
        signal = int(data.get("signal"))
    except (TypeError, ValueError):
        signal = 0
    if not title or signal not in VALID_SIGNALS:
        return jsonify({"error": "A title and signal (1 or -1) are required."}), 400

    existing = Feedback.query.filter_by(
        user_id=current_user.id, title=title, artist=artist
    ).first()
    if existing is not None:
        if existing.signal == signal:  # same reaction again → toggle off
            db.session.delete(existing)
            db.session.commit()
            return jsonify({"state": "cleared"})
        existing.signal = signal  # flip like <-> dislike
        db.session.commit()
        return jsonify({"state": "liked" if signal > 0 else "disliked"})

    db.session.add(
        Feedback(
            user_id=current_user.id,
            title=title,
            artist=artist,
            genre=(data.get("genre") or None),
            mood=(data.get("mood") or None),
            vibe=(data.get("vibe") or None),
            energy=_num(data.get("energy")),
            valence=_num(data.get("valence")),
            signal=signal,
            prompt=(data.get("query") or None),
        )
    )
    db.session.commit()
    return jsonify({"state": "liked" if signal > 0 else "disliked"})


@bp.get("/api/feedback")
@login_required
def list_feedback():
    rows = Feedback.query.filter_by(user_id=current_user.id).all()
    return jsonify({"feedback": [r.to_dict() for r in rows]})


@bp.get("/api/profile")
@login_required
def get_profile():
    rows = Feedback.query.filter_by(user_id=current_user.id).all()
    return jsonify({"profile": personalize.summary(personalize.build_profile(rows))})
