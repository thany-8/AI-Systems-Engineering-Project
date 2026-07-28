"""Taste-profile logic: turn a user's *history* — 👍 / 👎 reactions **and** the
songs in their saved playlists — into a weighted preference profile, score how
well a candidate song matches it, and explain *why*.

Kept free of Flask/DB imports so the ranking bias is deterministic and
unit-testable: it operates on plain feedback rows (exposing ``signal``, ``vibe``,
``genre``, ``artist``, ``energy``) and song dicts.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

# Signal weights — an explicit reaction counts more than an implicit "save".
LIKE_WEIGHT = 1.0
DISLIKE_WEIGHT = -1.0
SAVED_WEIGHT = 0.5


def _norm(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def build_profile(feedback_rows, saved_songs=None, saved_playlists=0):
    """Aggregate a user's reactions and saved-playlist songs into weighted
    per-attribute preferences (positive = liked, negative = avoided)."""
    vibe: dict[str, float] = defaultdict(float)
    genre: dict[str, float] = defaultdict(float)
    artist: dict[str, float] = defaultdict(float)
    energy_num = energy_den = 0.0
    likes = dislikes = 0

    def add(weight, v, g, a, energy):
        nonlocal energy_num, energy_den
        if v:
            vibe[v] += weight
        if g:
            genre[g] += weight
        if a:
            artist[a] += weight
        if weight > 0 and energy is not None:
            try:
                energy_num += weight * float(energy)
                energy_den += weight
            except (TypeError, ValueError):
                pass

    for row in feedback_rows or []:
        positive = (getattr(row, "signal", 0) or 0) > 0
        likes, dislikes = (likes + 1, dislikes) if positive else (likes, dislikes + 1)
        add(
            LIKE_WEIGHT if positive else DISLIKE_WEIGHT,
            _norm(getattr(row, "vibe", None)),
            _norm(getattr(row, "genre", None)),
            _norm(getattr(row, "artist", None)),
            getattr(row, "energy", None),
        )

    songs = saved_songs or []
    for song in songs:
        add(
            SAVED_WEIGHT,
            _norm(song.get("vibe")),
            _norm(song.get("genre")),
            _norm(song.get("artist")),
            song.get("energy"),
        )

    return {
        "vibe": dict(vibe),
        "genre": dict(genre),
        "artist": dict(artist),
        "pref_energy": (energy_num / energy_den) if energy_den else None,
        "likes": likes,
        "dislikes": dislikes,
        "saved_playlists": saved_playlists,
        "saved_songs": len(songs),
        "n": likes + dislikes + len(songs),
    }


def has_signal(profile) -> bool:
    """True when the profile carries any history to learn from."""
    return bool(profile) and profile.get("n", 0) > 0


def _clip(value: float) -> float:
    return max(-1.0, min(1.0, value))


def score(song, profile) -> float:
    """Taste match in ``[-1, 1]``: positive means the song resembles the user's
    history (liked vibes/genres/artists), negative means it resembles avoided
    ones."""
    if not has_signal(profile):
        return 0.0
    vibe = _norm(song.get("vibe"))
    genre = _norm(song.get("genre"))
    artist = _norm(song.get("artist"))
    value = (
        0.5 * _clip(profile["vibe"].get(vibe, 0.0))
        + 0.4 * _clip(profile["genre"].get(genre, 0.0))
        + 0.5 * _clip(profile["artist"].get(artist, 0.0))
    )
    return _clip(value)


def explain(song, profile):
    """The single most salient reason a song was biased, or ``None``.

    e.g. ``{"dir": "up", "text": "you like Neon Echo"}``.
    """
    if not has_signal(profile):
        return None
    vibe = _norm(song.get("vibe"))
    genre = _norm(song.get("genre"))
    artist = _norm(song.get("artist"))
    av = profile["artist"].get(artist, 0.0)
    gv = profile["genre"].get(genre, 0.0)
    vv = profile["vibe"].get(vibe, 0.0)

    candidates: list[tuple[float, str, str]] = []
    if av > 0:
        candidates.append((abs(av) + 0.3, "up", f"you like {song.get('artist')}"))
    if gv > 0:
        candidates.append((abs(gv) + 0.15, "up", f"you like {song.get('genre')}"))
    elif gv < 0:
        candidates.append((abs(gv) + 0.15, "down", f"you skip {song.get('genre')}"))
    if vv > 0:
        candidates.append((abs(vv), "up", f"matches your {vibe} taste"))
    elif vv < 0:
        candidates.append((abs(vv), "down", f"not your usual {vibe}"))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    _, direction, text = candidates[0]
    return {"dir": direction, "text": text}


def _intensity_label(energy: float) -> str:
    return "high" if energy >= 0.66 else "low" if energy <= 0.4 else "medium"


def summary(profile):
    """JSON-friendly taste profile for the UI (net preferences + sources)."""
    if not has_signal(profile):
        return {
            "n": 0, "likes": 0, "dislikes": 0, "saved_playlists": 0, "saved_songs": 0,
            "top_vibes": [], "top_genres": [], "top_artists": [],
            "disliked_vibes": [], "intensity": None, "pref_energy": None,
        }

    def top(pref, positive=True, k=3):
        items = [(name, w) for name, w in pref.items() if (w > 0 if positive else w < 0)]
        items.sort(key=lambda item: abs(item[1]), reverse=True)
        return [{"name": name, "weight": round(w, 2)} for name, w in items[:k]]

    pref_energy = profile.get("pref_energy")
    return {
        "n": profile["n"],
        "likes": profile["likes"],
        "dislikes": profile["dislikes"],
        "saved_playlists": profile.get("saved_playlists", 0),
        "saved_songs": profile.get("saved_songs", 0),
        "top_vibes": top(profile["vibe"], True),
        "top_genres": top(profile["genre"], True),
        "top_artists": top(profile["artist"], True),
        "disliked_vibes": top(profile["vibe"], False),
        "intensity": None if pref_energy is None else _intensity_label(pref_energy),
        "pref_energy": None if pref_energy is None else round(pref_energy, 2),
    }
