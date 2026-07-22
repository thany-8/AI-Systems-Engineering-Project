"""Build the RAG retrieval corpus: one rich text document per song.

Retrieval quality depends on having descriptive text to match against, but the
Module 3 dataset only has structured columns. So for each song we synthesise a
natural-language description from its attributes (energy, tempo, valence, …).
These documents are the *source* the assistant retrieves from before answering.
"""
from __future__ import annotations

import sys
from typing import Any

from app import config

# Reuse the Module 3 CSV loader (keeps a single source of truth for the data).
sys.path.insert(0, str(config.RECOMMENDER_DIR / "src"))
import recommender as music  # noqa: E402


def _energy_word(value: float) -> str:
    return "high-energy" if value >= 0.7 else "low-energy" if value < 0.4 else "medium-energy"


def _tempo_word(bpm: float) -> str:
    return "fast" if bpm >= 120 else "slow" if bpm < 90 else "mid"


def _valence_word(value: float) -> str:
    return "upbeat and positive" if value >= 0.7 else "sad and melancholic" if value < 0.4 else "neutral"


def _dance_word(value: float) -> str:
    return "very danceable" if value >= 0.7 else "not very danceable" if value < 0.5 else "moderately danceable"


def _acoustic_word(value: float) -> str:
    return "acoustic" if value >= 0.6 else "electronic/produced" if value < 0.2 else "lightly acoustic"


def _contexts(song: dict[str, Any]) -> str:
    """Suggest listening contexts so queries like 'study music' can match."""
    tags: list[str] = []
    if song["energy"] < 0.45 and song["valence"] >= 0.45:
        tags += ["studying", "focus", "relaxing", "reading"]
    if song["energy"] >= 0.75 and song["danceability"] >= 0.7:
        tags += ["working out", "workout", "gym", "party", "dancing"]
    if song["valence"] < 0.4:
        tags += ["a rainy day", "reflecting"]
    if song["acousticness"] >= 0.6:
        tags += ["a calm evening", "coffee shop"]
    if not tags:
        tags = ["everyday listening"]
    return "Good for " + ", ".join(dict.fromkeys(tags)) + "."


def describe(song: dict[str, Any]) -> str:
    """Return a natural-language description document for one song."""
    return (
        f"{song['title']} by {song['artist']} is a {song['mood']} {song['genre']} song. "
        f"It is {_energy_word(song['energy'])} with a {_tempo_word(song['tempo_bpm'])} tempo, "
        f"feels {_valence_word(song['valence'])}, is {_dance_word(song['danceability'])}, "
        f"and sounds {_acoustic_word(song['acousticness'])}. "
        f"{_contexts(song)}"
    )


_DOCUMENTS: list[dict[str, Any]] | None = None


def load_documents() -> list[dict[str, Any]]:
    """Load songs and attach a ``text`` field with the enriched description."""
    global _DOCUMENTS
    if _DOCUMENTS is None:
        songs = music.load_songs(str(config.SONGS_CSV))
        for song in songs:
            song["text"] = describe(song)
        _DOCUMENTS = songs
    return _DOCUMENTS
