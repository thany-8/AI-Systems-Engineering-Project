"""Reasoning layer: turn a user message into tool calls, and tool results into
a grounded answer.

Two interchangeable backends implement the same ``Planner`` interface:

* ``GeminiPlanner``  — Google Gemini (free tier). Used when ``GEMINI_API_KEY``
  is set. Robust: any error falls back to the offline planner.
* ``OfflinePlanner`` — deterministic keyword/heuristic planner + templated
  composer. Keeps the whole app runnable and testable with no API key.

Both only ever *propose* tool calls; execution and validation happen in
``tools``/``guardrails``. The composer cites songs in double quotes so the
grounding guardrail can verify them.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from app import config, engines, tools


@dataclass
class Decision:
    """A planner's decision for one step."""

    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    final: str | None = None  # set when no tools are needed (chat / help)


# ── Keyword vocab ─────────────────────────────────────────────────────────
_MUSIC_WORDS = ("music", "song", "songs", "playlist", "listen", "tune", "track", "vibe")
# Strong scheduling intent only. Activity words (walk/groom/…) are deliberately
# excluded here so "calm songs for grooming" is treated as a music request, not
# a request to build a care plan.
_SCHEDULE_WORDS = (
    "plan", "schedule", "day", "today", "task", "tasks", "routine",
    "agenda", "itinerary", "to-do", "todo",
)
_HELP_WORDS = ("help", "what can you", "who are you", "hello", "hi ", "hey", "capab")

_ACTIVITY_SYNONYMS = {
    "walk": "walk", "walking": "walk",
    "groom": "grooming", "grooming": "grooming", "brush": "grooming",
    "feed": "feeding", "feeding": "feeding",
    "play": "play", "playing": "play",
    "medicine": "medicine", "meds": "medicine", "medication": "medicine",
}
_ENERGY_WORDS = {
    "calm": 0.30, "chill": 0.30, "relax": 0.30, "relaxed": 0.30, "sleepy": 0.20,
    "focus": 0.40, "study": 0.40,
    "energetic": 0.85, "upbeat": 0.85, "intense": 0.90, "workout": 0.90,
    "hype": 0.90, "party": 0.85,
}

HELP_TEXT = (
    "I'm PawPal+ Companion. I can (1) plan your pets' care day — just tell me "
    "how many minutes you have (e.g. \"plan my day, I have 45 minutes\"), and "
    "(2) recommend music by mood, genre, or the activity you're doing (e.g. "
    "\"calm songs for grooming\"). Ask me both at once and I'll do them together."
)


def _has(text: str, words) -> bool:
    return any(w in text for w in words)


def _minutes(text: str) -> int | None:
    m = re.search(r"(\d+)\s*(?:hours?|hrs?)\b", text)
    if m:
        return int(m.group(1)) * 60
    m = re.search(r"(\d+)\s*(?:minutes?|mins?)\b", text)
    if m:
        return int(m.group(1))
    if "half an hour" in text:
        return 30
    if "an hour" in text:
        return 60
    return None


def _match_vocab(text: str, vocab) -> str | None:
    for term in sorted(vocab, key=len, reverse=True):
        if re.search(r"\b" + re.escape(term) + r"\b", text):
            return term
    return None


def _catalog_vocab() -> tuple[set[str], set[str]]:
    catalog = engines.get_catalog()
    moods = {s["mood"].lower() for s in catalog}
    genres = {s["genre"].lower() for s in catalog}
    return moods, genres


# ── Offline (deterministic) planner ───────────────────────────────────────
class OfflinePlanner:
    """Keyword-driven planner + templated composer (no network)."""

    def plan(self, message: str) -> Decision:
        low = message.lower()
        wants_music = _has(low, _MUSIC_WORDS)
        # A bare time budget ("I have 45 minutes") implies scheduling too, but
        # not when the message is clearly only about music.
        wants_schedule = _has(low, _SCHEDULE_WORDS) or (
            _minutes(low) is not None and not wants_music
        )

        if _has(low, _HELP_WORDS) and not (wants_music or wants_schedule):
            return Decision(final=HELP_TEXT)

        calls: list[dict[str, Any]] = []
        if wants_schedule:
            args: dict[str, Any] = {}
            mins = _minutes(low)
            if mins is not None:
                args["available_minutes"] = mins
            for name in ("max", "luna"):
                if re.search(r"\b" + name + r"\b", low):
                    args["pet_name"] = name.capitalize()
            calls.append({"name": "plan_pet_day", "args": args})

        if wants_music:
            moods, genres = _catalog_vocab()
            args = {"k": 3}
            for word, canonical in _ACTIVITY_SYNONYMS.items():
                if re.search(r"\b" + word + r"\b", low):
                    args["activity"] = canonical
                    break
            mood = _match_vocab(low, moods)
            if mood:
                args["mood"] = mood
            genre = _match_vocab(low, genres)
            if genre:
                args["genre"] = genre
            for word, energy in _ENERGY_WORDS.items():
                if re.search(r"\b" + word + r"\b", low):
                    args["energy"] = energy
                    break
            calls.append({"name": "recommend_music", "args": args})

        if not calls:
            calls.append({"name": "list_pets_and_tasks", "args": {}})
        return Decision(tool_calls=calls)

    def compose(self, message: str, observations: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for obs in observations:
            tool, result = obs.get("tool"), obs.get("result")
            if obs.get("error"):
                parts.append(f"⚠ I couldn't run {tool}: {obs['error']}")
            elif tool == "plan_pet_day":
                parts.append(_render_plan(result))
            elif tool == "recommend_music":
                parts.append(_render_music(result))
            elif tool == "list_pets_and_tasks":
                parts.append(_render_pets(result))
        if not parts:
            return HELP_TEXT
        return "\n\n".join(p for p in parts if p)


# ── Templated renderers (grounded: songs cited in double quotes) ──────────
def _render_plan(plan: dict[str, Any]) -> str:
    lines = [f"🐾 Care plan for {plan['date']}:"]
    budget = plan.get("available_minutes")
    header = f"scheduled {plan['total_minutes']} min"
    if budget is not None:
        header += f" of your {budget}-min budget"
    lines.append(header + ".")
    if plan["included"]:
        for i, t in enumerate(plan["included"], 1):
            lines.append(
                f"  {i}. {t['time']} — {t['task_type']} for {t['pet']} "
                f"({t['priority']} priority, {t['duration']} min)"
            )
    else:
        lines.append("  Nothing fits — try a larger time budget.")
    for s in plan["skipped"]:
        t = s["task"]
        lines.append(f"  • Skipped {t['task_type']} for {t['pet']}: {s['reason']}.")
    for c in plan["conflicts"]:
        a, b = c["a"], c["b"]
        lines.append(
            f"  ⚠ Conflict: {a['task_type']} ({a['time']}) overlaps "
            f"{b['task_type']} ({b['time']}) for {a['pet']}."
        )
    return "\n".join(lines)


def _render_music(songs: list[dict[str, Any]]) -> str:
    if not songs:
        return "🎵 I couldn't find a good musical match for that."
    lines = ["🎵 Music picks:"]
    for s in songs:
        lines.append(
            f'  • "{s["title"]}" by {s["artist"]} '
            f'— {s["mood"]}, {s["genre"]} (match {s["score"]:.2f})'
        )
    return "\n".join(lines)


def _render_pets(data: dict[str, Any]) -> str:
    lines = [f"🐾 {data['owner']}'s pets:"]
    for name, info in data["pets"].items():
        lines.append(
            f"  • {name} ({info['species']}, age {info['age']}): "
            f"{len(info['tasks'])} care tasks"
        )
    lines.append("Ask me to plan the day or suggest music!")
    return "\n".join(lines)


# ── Gemini planner ────────────────────────────────────────────────────────
_PLAN_PROMPT = """You are the planner for PawPal+ Companion, a pet-care and music assistant.
Decide which tools (if any) to call to satisfy the user. Only use these tools:

{tools}

Rules:
- Respond with STRICT JSON only, no prose, no code fences.
- To call tools: {{"tool_calls": [{{"name": "<tool>", "args": {{...}}}}]}}
- If the user is only greeting or asking what you can do, respond:
  {{"final": "<short helpful reply>"}}
- Never invent pets, tasks, or song titles. Use tool args, not free text.

User message: {message}
JSON:"""

_COMPOSE_PROMPT = """You are PawPal+ Companion. Write a friendly, concise reply to the user
using ONLY the tool results below. Do not invent pets, tasks, or songs.
When you mention a song, wrap its EXACT title in double quotes.
Report skipped tasks and conflicts honestly.

User message: {message}

Tool results (JSON):
{data}

Reply:"""


class GeminiPlanner:
    """Google Gemini backend with automatic offline fallback on any error."""

    def __init__(self) -> None:
        import google.generativeai as genai  # lazy: only needed with a key

        genai.configure(api_key=config.GEMINI_API_KEY)
        self._genai = genai
        self._model = genai.GenerativeModel(config.GEMINI_MODEL)
        self._fallback = OfflinePlanner()

    def _generate(self, prompt: str, *, as_json: bool = False) -> str:
        gen_config = {"response_mime_type": "application/json"} if as_json else None
        resp = self._model.generate_content(
            prompt,
            generation_config=gen_config,
            request_options={"timeout": config.LLM_TIMEOUT_S},
        )
        return getattr(resp, "text", "") or ""

    def plan(self, message: str) -> Decision:
        try:
            raw = self._generate(
                _PLAN_PROMPT.format(tools=tools.tools_prompt(), message=message),
                as_json=True,
            )
            data = _extract_json(raw)
            if data.get("final"):
                return Decision(final=str(data["final"]))
            calls = [
                {"name": c.get("name"), "args": c.get("args") or {}}
                for c in (data.get("tool_calls") or [])
                if isinstance(c, dict) and c.get("name")
            ]
            return Decision(tool_calls=calls) if calls else self._fallback.plan(message)
        except Exception:
            return self._fallback.plan(message)

    def compose(self, message: str, observations: list[dict[str, Any]]) -> str:
        try:
            text = self._generate(
                _COMPOSE_PROMPT.format(
                    message=message, data=json.dumps(observations, default=str, indent=2)
                )
            ).strip()
            return text or self._fallback.compose(message, observations)
        except Exception:
            return self._fallback.compose(message, observations)


def _extract_json(text: str) -> dict[str, Any]:
    """Parse the first JSON object from a model response (tolerates fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, depth = text.find("{"), 0
        if start == -1:
            return {}
        for i in range(start, len(text)):
            depth += text[i] == "{"
            depth -= text[i] == "}"
            if depth == 0:
                return json.loads(text[start : i + 1])
        return {}


def get_planner():
    """Return the active planner based on configuration."""
    return GeminiPlanner() if config.USE_LLM else OfflinePlanner()
