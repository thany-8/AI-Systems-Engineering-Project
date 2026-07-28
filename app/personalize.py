"""Taste-profile logic: turn a user's 👍/👎 feedback into a preference profile
and score how well a candidate song matches it.

Kept free of Flask/DB imports so it stays deterministic and unit-testable — it
operates on plain feedback rows (anything exposing ``signal``, ``vibe``,
``genre``, ``artist`` and ``energy``).
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def build_profile(rows: list[Any]) -> dict[str, Any]:
    """Aggregate feedback rows into a taste profile."""
    liked_vibes, disliked_vibes = Counter(), Counter()
    liked_genres, disliked_genres = Counter(), Counter()
    liked_artists, disliked_artists = Counter(), Counter()
    liked_energies: list[float] = []
    likes = dislikes = 0

    for row in rows:
        positive = (getattr(row, "signal", 0) or 0) > 0
        vibe = (getattr(row, "vibe", None) or "").lower()
        genre = (getattr(row, "genre", None) or "").lower()
        artist = (getattr(row, "artist", None) or "").lower()
        energy = getattr(row, "energy", None)

        if positive:
            likes += 1
            if vibe:
                liked_vibes[vibe] += 1
            if genre:
                liked_genres[genre] += 1
            if artist:
                liked_artists[artist] += 1
            if energy is not None:
                liked_energies.append(float(energy))
        else:
            dislikes += 1
            if vibe:
                disliked_vibes[vibe] += 1
            if genre:
                disliked_genres[genre] += 1
            if artist:
                disliked_artists[artist] += 1

    return {
        "liked_vibes": liked_vibes,
        "disliked_vibes": disliked_vibes,
        "liked_genres": liked_genres,
        "disliked_genres": disliked_genres,
        "liked_artists": liked_artists,
        "disliked_artists": disliked_artists,
        "pref_energy": (sum(liked_energies) / len(liked_energies)) if liked_energies else None,
        "likes": likes,
        "dislikes": dislikes,
        "n": likes + dislikes,
    }


def has_signal(profile: dict[str, Any] | None) -> bool:
    """True when the profile carries at least one reaction to learn from."""
    return bool(profile) and profile.get("n", 0) > 0


def score(song: dict[str, Any], profile: dict[str, Any] | None) -> float:
    """Return a taste-match score in ``[-1, 1]`` for a candidate song.

    Positive means it resembles songs the user liked; negative means it
    resembles ones they disliked (a disliked artist is penalised most).
    """
    if not has_signal(profile):
        return 0.0
    vibe = (song.get("vibe") or "").lower()
    genre = (song.get("genre") or "").lower()
    artist = (song.get("artist") or "").lower()

    value = 0.0
    if vibe in profile["liked_vibes"]:
        value += 0.5
    if vibe in profile["disliked_vibes"]:
        value -= 0.5
    if genre in profile["liked_genres"]:
        value += 0.4
    if genre in profile["disliked_genres"]:
        value -= 0.4
    if artist in profile["liked_artists"]:
        value += 0.4
    if artist in profile["disliked_artists"]:
        value -= 0.6
    return max(-1.0, min(1.0, value))


def _intensity_label(energy: float) -> str:
    return "high" if energy >= 0.66 else "low" if energy <= 0.4 else "medium"


def summary(profile: dict[str, Any]) -> dict[str, Any]:
    """A JSON-friendly view of the profile for the UI."""
    if not has_signal(profile):
        return {
            "n": 0,
            "likes": 0,
            "dislikes": 0,
            "top_vibes": [],
            "top_genres": [],
            "top_artists": [],
            "disliked_vibes": [],
            "intensity": None,
            "pref_energy": None,
        }

    def top(counter: Counter, k: int = 3) -> list[dict[str, Any]]:
        return [{"name": name, "count": count} for name, count in counter.most_common(k)]

    pref_energy = profile.get("pref_energy")
    return {
        "n": profile["n"],
        "likes": profile["likes"],
        "dislikes": profile["dislikes"],
        "top_vibes": top(profile["liked_vibes"]),
        "top_genres": top(profile["liked_genres"]),
        "top_artists": top(profile["liked_artists"]),
        "disliked_vibes": top(profile["disliked_vibes"]),
        "intensity": None if pref_energy is None else _intensity_label(pref_energy),
        "pref_energy": None if pref_energy is None else round(pref_energy, 2),
    }
