"""Saved-playlist API scoped to the signed-in user.

A playlist bundles the original prompt, the detected vibe, the grounded note,
and the list of recommended songs (persisted as JSON in :class:`Playlist`).
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Playlist

bp = Blueprint("playlists", __name__, url_prefix="/api/playlists")

MAX_TITLE = 200
MAX_PROMPT = 2000
MAX_SONGS = 50


@bp.get("")
@login_required
def list_playlists():
    return jsonify({"playlists": [p.to_dict() for p in current_user.playlists]})


@bp.post("")
@login_required
def create_playlist():
    data = request.get_json(silent=True) or {}
    songs = data.get("songs")
    prompt = (data.get("prompt") or "").strip()

    if not isinstance(songs, list) or not songs:
        return jsonify({"error": "A playlist needs at least one song."}), 400
    if not prompt:
        return jsonify({"error": "Missing the playlist prompt."}), 400

    title = (data.get("title") or prompt).strip()[:MAX_TITLE] or "Untitled playlist"
    playlist = Playlist(
        user_id=current_user.id,
        title=title,
        prompt=prompt[:MAX_PROMPT],
        vibe=(data.get("vibe") or None),
        note=(data.get("note") or None),
    )
    playlist.songs = songs[:MAX_SONGS]
    db.session.add(playlist)
    db.session.commit()
    return jsonify({"playlist": playlist.to_dict()}), 201


@bp.delete("/<int:playlist_id>")
@login_required
def delete_playlist(playlist_id: int):
    playlist = db.session.get(Playlist, playlist_id)
    if playlist is None or playlist.user_id != current_user.id:
        return jsonify({"error": "Playlist not found."}), 404
    db.session.delete(playlist)
    db.session.commit()
    return jsonify({"ok": True})
