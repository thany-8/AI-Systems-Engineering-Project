"""Authentication API: signup, login, logout, and current-user lookup.

Every endpoint speaks JSON so the single-page frontend can manage accounts with
``fetch``. Sessions are cookie-based via Flask-Login, and passwords are only ever
stored as a salted Werkzeug hash (see :mod:`app.models`).
"""
from __future__ import annotations

import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


def _clean_email(value: object) -> str:
    return (value or "").strip().lower() if isinstance(value, str) else ""


@bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = _clean_email(data.get("email"))
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or None

    if not _EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < MIN_PASSWORD:
        return (
            jsonify({"error": f"Password must be at least {MIN_PASSWORD} characters."}),
            400,
        )
    if User.query.filter_by(email=email).first() is not None:
        return jsonify({"error": "An account with that email already exists."}), 409

    user = User(email=email, display_name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"user": user.to_dict()}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = _clean_email(data.get("email"))
    password = data.get("password") or ""
    remember = bool(data.get("remember", True))

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Incorrect email or password."}), 401

    login_user(user, remember=remember)
    return jsonify({"user": user.to_dict()})


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    if current_user.is_authenticated:
        return jsonify({"user": current_user.to_dict()})
    return jsonify({"user": None})
