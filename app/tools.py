"""The agent's action space: tools that wrap the two Module engines.

Each tool has a JSON-schema-ish spec (used both to prompt the LLM and to
validate its requests) and a handler that calls into ``engines``. Nothing here
talks to the LLM — tools are pure, deterministic capabilities.
"""
from __future__ import annotations

import json
from typing import Any

from app import engines, guardrails

TOOLS: dict[str, dict[str, Any]] = {
    "plan_pet_day": {
        "description": (
            "Build a prioritised daily pet-care plan: which tasks to do, in "
            "what order, fitting an optional time budget and reporting skips "
            "and conflicts."
        ),
        "parameters": {
            "available_minutes": {
                "type": "integer",
                "description": "Minutes the owner has available today.",
                "min": 1,
                "max": 1440,
            },
            "target_date": {
                "type": "string",
                "description": "ISO date (YYYY-MM-DD). Defaults to today.",
            },
            "pet_name": {
                "type": "string",
                "description": "Restrict the plan to one pet (e.g. Max or Luna).",
            },
        },
        "handler": lambda **kw: engines.plan_pet_day(**kw),
    },
    "recommend_music": {
        "description": (
            "Recommend songs from the catalog by mood, energy (0-1), genre, or "
            "a pet activity (e.g. calm music for grooming). Returns scored, "
            "explained picks."
        ),
        "parameters": {
            "mood": {"type": "string", "description": "Desired mood, e.g. calm, happy."},
            "energy": {
                "type": "number",
                "description": "Target energy from 0 (calm) to 1 (intense).",
                "min": 0.0,
                "max": 1.0,
            },
            "genre": {"type": "string", "description": "Preferred genre, e.g. pop."},
            "activity": {
                "type": "string",
                "description": "Pet activity to match music to.",
                "enum": list(engines.ACTIVITY_VIBES.keys()),
            },
            "k": {
                "type": "integer",
                "description": "How many songs to return.",
                "min": 1,
                "max": 10,
            },
        },
        "handler": lambda **kw: engines.recommend_music(**kw),
    },
    "list_pets_and_tasks": {
        "description": "List the household's pets and each pet's care tasks.",
        "parameters": {},
        "handler": lambda **kw: engines.list_pets_and_tasks(),
    },
}


def tools_prompt() -> str:
    """Render the tool catalog as compact JSON for the LLM planner prompt."""
    catalog = {
        name: {
            "description": spec["description"],
            "parameters": spec["parameters"],
        }
        for name, spec in TOOLS.items()
    }
    return json.dumps(catalog, indent=2)


def execute(name: str, args: dict[str, Any] | None) -> Any:
    """Validate then run a tool call. Raises ``GuardrailError`` on bad input."""
    clean = guardrails.validate_tool_call(name, args or {}, TOOLS)
    return TOOLS[name]["handler"](**clean)
