"""Adapter around the two Module engines.

This module is what makes the app a genuine *combination* of both subsystems:
it imports and calls the real code from ``module2-pawpal`` (the PawPal+
scheduler) and ``module3-music-recommender`` (the content-based recommender)
rather than reimplementing their logic. Everything the agent can *do* is
exposed here as plain, JSON-serialisable functions.
"""
from __future__ import annotations

import sys
from datetime import date
from typing import Any

from app import config

# Make the hyphenated sibling folders importable as top-level modules.
for _path in (str(config.PAWPAL_DIR), str(config.RECOMMENDER_DIR / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import pawpal_system as pawpal  # noqa: E402  Module 2 engine
import recommender as music     # noqa: E402  Module 3 engine


# ── PawPal+ scheduling ────────────────────────────────────────────────────

def build_default_schedule() -> "pawpal.Schedule":
    """Build a realistic sample household so the scheduler has data to plan.

    A fresh, deterministic schedule is created on every call (no shared mutable
    state), which keeps tool executions independent and easy to test.
    """
    today = date.today().isoformat()
    owner = pawpal.Owner("Tania", "tania@example.com")
    max_ = pawpal.Pet(name="Max", age=4, species="dog")
    luna = pawpal.Pet(name="Luna", age=2, species="cat")
    owner.add_pet(max_)
    owner.add_pet(luna)

    schedule = pawpal.Schedule(owner)
    for task in (
        pawpal.Task(task_type="walk", pet=max_, date=today, time="08:00",
                    description="Morning walk in the park", frequency="daily",
                    duration=30, priority="medium"),
        pawpal.Task(task_type="feeding", pet=max_, date=today, time="12:00",
                    description="Dry kibble — one cup", frequency="daily",
                    duration=10, priority="medium"),
        pawpal.Task(task_type="grooming", pet=max_, date=today, time="17:30",
                    description="Brush-down and nail check", frequency="weekly",
                    duration=25, priority="high"),
        pawpal.Task(task_type="medicine", pet=luna, date=today, time="09:30",
                    description="Flea treatment drops", frequency="monthly",
                    duration=5, priority="high"),
        pawpal.Task(task_type="play", pet=luna, date=today, time="18:00",
                    description="Feather-wand play session", frequency="daily",
                    duration=15, priority="low"),
    ):
        schedule.add_task(task)
    return schedule


def _task_dict(task: "pawpal.Task") -> dict[str, Any]:
    return {
        "task_type": task.task_type,
        "pet": task.pet.name,
        "date": task.date,
        "time": task.time,
        "duration": task.duration,
        "priority": task.priority,
        "frequency": task.frequency,
        "description": task.description,
        "status": task.status,
    }


def plan_pet_day(
    available_minutes: int | None = None,
    target_date: str | None = None,
    pet_name: str | None = None,
) -> dict[str, Any]:
    """Build a prioritised daily care plan using the PawPal+ engine."""
    schedule = build_default_schedule()
    if pet_name:
        wanted = pet_name.strip().lower()
        schedule.tasks = [t for t in schedule.tasks if t.pet.name.lower() == wanted]

    plan = schedule.plan_day(target_date=target_date, available_minutes=available_minutes)
    return {
        "date": plan.date,
        "available_minutes": plan.available_minutes,
        "total_minutes": plan.total_minutes,
        "included": [_task_dict(t) for t in plan.included],
        "skipped": [{"task": _task_dict(t), "reason": r} for t, r in plan.skipped],
        "conflicts": [
            {"a": _task_dict(a), "b": _task_dict(b)} for a, b in plan.conflicts
        ],
        "explanation": plan.explain(),
    }


def list_pets_and_tasks() -> dict[str, Any]:
    """Return the current household: pets and their care tasks."""
    schedule = build_default_schedule()
    pets: dict[str, Any] = {}
    for task in schedule.tasks:
        entry = pets.setdefault(
            task.pet.name,
            {"species": task.pet.species, "age": task.pet.age, "tasks": []},
        )
        entry["tasks"].append(_task_dict(task))
    return {"owner": schedule.owner.name, "pets": pets}


# ── Music recommendation ──────────────────────────────────────────────────

# Maps a pet activity to a musical "vibe" so the agent can pick music that
# suits what the owner is doing (e.g. calm music while grooming).
ACTIVITY_VIBES: dict[str, dict[str, Any]] = {
    "walk": {"moods": ["energetic", "happy"], "energy": 0.80},
    "play": {"moods": ["happy", "party", "energetic"], "energy": 0.85},
    "feeding": {"moods": ["happy", "relaxed"], "energy": 0.50},
    "grooming": {"moods": ["calm", "relaxed", "chill"], "energy": 0.35},
    "medicine": {"moods": ["calm", "relaxed", "chill"], "energy": 0.30},
}

_CATALOG: list[dict[str, Any]] | None = None


def get_catalog() -> list[dict[str, Any]]:
    """Load (and cache) the song catalog from the Module 3 dataset."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = music.load_songs(str(config.SONGS_CSV))
    return _CATALOG


def recommend_music(
    mood: str | None = None,
    energy: float | None = None,
    genre: str | None = None,
    activity: str | None = None,
    k: int = 3,
) -> list[dict[str, Any]]:
    """Recommend songs via the Module 3 content-based scorer.

    Preferences may come from an explicit mood/energy/genre or be derived from a
    pet *activity*. If nothing usable is supplied we fall back to the project's
    sample taste profile so the tool always returns sensible, grounded picks.
    """
    moods: list[str] = []
    if mood:
        moods.append(mood)
    vibe = ACTIVITY_VIBES.get((activity or "").lower(), {})
    moods.extend(vibe.get("moods", []))

    target_energy = energy if energy is not None else vibe.get("energy")

    prefs: dict[str, Any] = {}
    if moods:
        prefs["favorite_moods"] = moods
    if genre:
        prefs["favorite_genres"] = [genre]
    if target_energy is not None:
        prefs["target_energy"] = target_energy

    if not prefs:
        try:
            from user_profile import user_profile as default_profile
            prefs = dict(default_profile)
        except Exception:
            prefs = {"favorite_moods": ["happy"], "target_energy": 0.6}

    results = music.recommend_songs(prefs, get_catalog(), k=max(1, int(k)))
    return [
        {
            "title": song["title"],
            "artist": song["artist"],
            "genre": song["genre"],
            "mood": song["mood"],
            "energy": song["energy"],
            "score": round(float(score), 3),
            "reason": reason,
        }
        for song, score, reason in results
    ]
