"""Database models: user accounts and their saved playlists.

Passwords are never stored in plain text — only a salted hash produced by
Werkzeug's :func:`generate_password_hash` is persisted.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """A registered account able to generate and save playlists."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=_utcnow)

    playlists = db.relationship(
        "Playlist",
        backref="user",
        cascade="all, delete-orphan",
        order_by="Playlist.created_at.desc()",
        lazy=True,
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def name(self) -> str:
        return self.display_name or self.email.split("@", 1)[0]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "email": self.email, "name": self.name}


class Playlist(db.Model):
    """A generated playlist saved by a user (songs stored as JSON)."""

    __tablename__ = "playlists"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    prompt = db.Column(db.String(2000), nullable=False)
    vibe = db.Column(db.String(40))
    note = db.Column(db.Text)
    songs_json = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, default=_utcnow)

    @property
    def songs(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.songs_json)
        except (TypeError, ValueError):
            return []

    @songs.setter
    def songs(self, value: list[dict[str, Any]] | None) -> None:
        self.songs_json = json.dumps(value or [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "prompt": self.prompt,
            "vibe": self.vibe,
            "note": self.note,
            "songs": self.songs,
            "created_at": (self.created_at or _utcnow()).isoformat(),
        }


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    if not user_id:
        return None
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
