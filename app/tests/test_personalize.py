"""Tests for intensity nuance + taste-profile personalization.

Pure logic and pipeline behaviour run offline; the API tests use a throwaway
SQLite database via ``create_app``.
"""
from __future__ import annotations

import pytest

from app import personalize, pipeline
from app.server import create_app


class _Row:
    """Stand-in for a Feedback row for the pure profile logic."""

    def __init__(self, vibe, genre, artist, energy, signal):
        self.vibe, self.genre, self.artist = vibe, genre, artist
        self.energy, self.signal = energy, signal


# ── Intensity detection ────────────────────────────────────────────────────
def test_detect_intensity_directions():
    assert pipeline.detect_intensity("high-energy workout")["label"] == "high"
    assert pipeline.detect_intensity("mellow calm evening")["label"] == "low"
    assert pipeline.detect_intensity("medium intensity focus")["label"] == "medium"
    assert pipeline.detect_intensity("sad songs for a rainy day") is None


def test_detect_intensity_modifiers_and_negation():
    assert (
        pipeline.detect_intensity("super intense")["energy"]
        > pipeline.detect_intensity("intense")["energy"]
    )
    # "not too intense" should pull below a plain "intense"
    assert (
        pipeline.detect_intensity("not too intense workout")["energy"]
        < pipeline.detect_intensity("intense workout")["energy"]
    )


def test_resolve_intensity_explicit_override_wins():
    assert pipeline.resolve_intensity("anything", "high")["label"] == "high"
    assert pipeline.resolve_intensity("anything", 0.15)["label"] == "low"
    assert pipeline.resolve_intensity("plain query", None) is None


# ── Pipeline: intensity + defaults ─────────────────────────────────────────
def test_intensity_shifts_ranking_toward_target_energy():
    avg = lambda out: sum(s["energy"] for s in out["results"]) / len(out["results"])
    high = pipeline.recommend("songs to listen to", intensity="high")
    low = pipeline.recommend("songs to listen to", intensity="low")
    assert avg(high) > avg(low)
    assert high["desired_intensity"]["label"] == "high"
    assert low["desired_intensity"]["label"] == "low"


def test_recommend_unchanged_without_intensity_or_profile():
    out = pipeline.recommend("sad songs for a rainy day")
    assert out["desired_intensity"] is None
    assert out["personalized"] is False
    assert out["results"][0]["vibe"] == "melancholy"


# ── Taste profile logic ────────────────────────────────────────────────────
def test_build_profile_counts_genres_and_energy():
    profile = personalize.build_profile(
        [_Row("calm", "lofi", "loroom", 0.3, 1), _Row("upbeat", "pop", "x", 0.9, -1)]
    )
    assert profile["likes"] == 1 and profile["dislikes"] == 1
    assert "lofi" in profile["liked_genres"] and "pop" in profile["disliked_genres"]
    assert abs(profile["pref_energy"] - 0.3) < 1e-6
    assert personalize.has_signal(profile)


def test_score_rewards_liked_and_penalizes_disliked():
    profile = personalize.build_profile(
        [_Row("calm", "lofi", "loroom", 0.3, 1), _Row("upbeat", "pop", "x", 0.9, -1)]
    )
    liked = personalize.score({"vibe": "calm", "genre": "lofi", "artist": "loroom"}, profile)
    disliked = personalize.score({"vibe": "upbeat", "genre": "pop", "artist": "x"}, profile)
    assert liked > 0 > disliked


def test_empty_profile_is_neutral():
    empty = personalize.build_profile([])
    assert personalize.score({"vibe": "calm"}, empty) == 0.0
    assert not personalize.has_signal(empty)
    assert personalize.summary(empty)["n"] == 0


def test_summary_uses_net_vibe_preference():
    # the same vibe liked once and disliked once cancels out (appears in neither)
    profile = personalize.build_profile(
        [
            _Row("upbeat", "pop", "a", 0.8, 1),
            _Row("upbeat", "dance", "b", 0.8, -1),
            _Row("calm", "lofi", "c", 0.3, 1),
        ]
    )
    s = personalize.summary(profile)
    liked = {v["name"] for v in s["top_vibes"]}
    disliked = {v["name"] for v in s["disliked_vibes"]}
    assert "upbeat" not in liked and "upbeat" not in disliked
    assert "calm" in liked
    assert liked.isdisjoint(disliked)


def test_personalization_flags_and_scores_results():
    profile = personalize.build_profile([_Row("intense", "rock", "voltline", 0.9, 1)] * 2)
    out = pipeline.recommend("energetic songs", user_profile=profile)
    assert out["personalized"] is True
    assert any((r.get("personal_score") or 0) > 0 for r in out["results"])


# ── Feedback + profile API ─────────────────────────────────────────────────
@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 't.sqlite'}"}
    )
    with app.test_client() as test_client:
        yield test_client


def _signup(client, email="tania@example.com"):
    return client.post(
        "/api/auth/signup", json={"email": email, "password": "supersecret"}
    )


def _song(**overrides):
    base = {
        "title": "Storm Runner",
        "artist": "Voltline",
        "genre": "rock",
        "vibe": "intense",
        "energy": 0.9,
        "signal": 1,
    }
    base.update(overrides)
    return base


def test_feedback_and_profile_require_auth(client):
    assert client.post("/api/feedback", json=_song()).status_code == 401
    assert client.get("/api/profile").status_code == 401


def test_feedback_toggle_updates_profile(client):
    _signup(client)
    assert client.post("/api/feedback", json=_song()).get_json()["state"] == "liked"

    profile = client.get("/api/profile").get_json()["profile"]
    assert profile["likes"] == 1
    assert profile["top_genres"][0]["name"] == "rock"

    # same reaction again clears it
    assert client.post("/api/feedback", json=_song()).get_json()["state"] == "cleared"
    assert client.get("/api/profile").get_json()["profile"]["n"] == 0

    # dislike, then flip back to like
    assert client.post("/api/feedback", json=_song(signal=-1)).get_json()["state"] == "disliked"
    assert client.post("/api/feedback", json=_song(signal=1)).get_json()["state"] == "liked"


def test_feedback_validation(client):
    _signup(client)
    assert client.post("/api/feedback", json=_song(title="")).status_code == 400
    assert client.post("/api/feedback", json=_song(signal=5)).status_code == 400


def test_feedback_is_isolated_per_user(client):
    _signup(client, email="a@example.com")
    client.post("/api/feedback", json=_song())
    client.post("/api/auth/logout")

    _signup(client, email="b@example.com")
    assert client.get("/api/feedback").get_json()["feedback"] == []
    assert client.get("/api/profile").get_json()["profile"]["n"] == 0


def test_recommend_personalizes_over_http(client):
    _signup(client)
    client.post("/api/feedback", json=_song())
    body = client.post("/api/recommend", json={"query": "energetic songs"}).get_json()
    assert body["personalized"] is True


def test_recommend_intensity_over_http(client):
    body = client.post(
        "/api/recommend", json={"query": "songs", "intensity": "low"}
    ).get_json()
    assert body["desired_intensity"]["label"] == "low"
