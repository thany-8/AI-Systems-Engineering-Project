"""Tests for user accounts and saved playlists.

Each test runs against a throwaway SQLite database created via
``create_app`` so real data (``app/app.sqlite``) is never touched.
"""
from __future__ import annotations

import pytest

from app.server import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite'}",
        }
    )
    with app.test_client() as test_client:
        yield test_client


def _signup(client, email="tania@example.com", password="supersecret", name="Tania"):
    return client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "name": name},
    )


def _songs():
    return [
        {
            "title": "Someone Like You",
            "artist": "Adele",
            "genre": "pop",
            "mood": "sad",
            "vibe": "melancholy",
            "final_score": 0.97,
        }
    ]


# ── Signup / login / session ───────────────────────────────────────────────
def test_signup_creates_and_logs_in(client):
    res = _signup(client)
    assert res.status_code == 201
    assert res.get_json()["user"]["email"] == "tania@example.com"
    assert client.get("/api/auth/me").get_json()["user"]["name"] == "Tania"


def test_signup_validates_email_and_password(client):
    bad_email = client.post(
        "/api/auth/signup", json={"email": "nope", "password": "supersecret"}
    )
    assert bad_email.status_code == 400
    short_pw = client.post(
        "/api/auth/signup", json={"email": "a@b.com", "password": "short"}
    )
    assert short_pw.status_code == 400


def test_signup_rejects_duplicate_email(client):
    assert _signup(client).status_code == 201
    assert _signup(client, name="Someone else").status_code == 409


def test_login_logout_flow(client):
    _signup(client)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").get_json()["user"] is None

    bad = client.post(
        "/api/auth/login", json={"email": "tania@example.com", "password": "wrong"}
    )
    assert bad.status_code == 401

    ok = client.post(
        "/api/auth/login",
        json={"email": "tania@example.com", "password": "supersecret"},
    )
    assert ok.status_code == 200
    assert client.get("/api/auth/me").get_json()["user"]["email"] == "tania@example.com"


def test_email_is_case_insensitive(client):
    _signup(client, email="Tania@Example.com")
    client.post("/api/auth/logout")
    ok = client.post(
        "/api/auth/login",
        json={"email": "tania@example.com", "password": "supersecret"},
    )
    assert ok.status_code == 200


def test_password_is_hashed_not_stored_plaintext(client):
    _signup(client)
    from app.models import User

    with client.application.app_context():
        user = User.query.filter_by(email="tania@example.com").first()
        assert user is not None
        assert "supersecret" not in (user.password_hash or "")
        assert user.check_password("supersecret")
        assert not user.check_password("wrong")


# ── Saved playlists ────────────────────────────────────────────────────────
def test_playlists_require_authentication(client):
    assert client.get("/api/playlists").status_code == 401
    assert (
        client.post("/api/playlists", json={"prompt": "x", "songs": _songs()}).status_code
        == 401
    )


def test_save_list_and_delete_playlist(client):
    _signup(client)
    created = client.post(
        "/api/playlists",
        json={
            "title": "Rainy day",
            "prompt": "sad songs for a rainy day",
            "vibe": "melancholy",
            "note": "A grounded explanation.",
            "songs": _songs(),
        },
    )
    assert created.status_code == 201
    playlist_id = created.get_json()["playlist"]["id"]

    listing = client.get("/api/playlists").get_json()["playlists"]
    assert len(listing) == 1
    assert listing[0]["title"] == "Rainy day"
    assert listing[0]["songs"][0]["title"] == "Someone Like You"

    assert client.delete(f"/api/playlists/{playlist_id}").status_code == 200
    assert client.get("/api/playlists").get_json()["playlists"] == []


def test_save_rejects_empty_songs(client):
    _signup(client)
    res = client.post("/api/playlists", json={"prompt": "x", "songs": []})
    assert res.status_code == 400


def test_users_cannot_touch_each_others_playlists(client):
    _signup(client, email="a@example.com")
    playlist_id = (
        client.post("/api/playlists", json={"prompt": "mine", "songs": _songs()})
        .get_json()["playlist"]["id"]
    )
    client.post("/api/auth/logout")

    _signup(client, email="b@example.com")
    assert client.get("/api/playlists").get_json()["playlists"] == []
    assert client.delete(f"/api/playlists/{playlist_id}").status_code == 404
