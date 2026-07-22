"""Grounded generation — the *Generation* in RAG.

Compose a music recommendation from the retrieved-and-ranked songs. With a
Gemini key the model writes the reply from that context; otherwise a
deterministic template is used. Either way the answer is built ONLY from the
supplied songs, and titles are wrapped in double quotes so the grounding
guardrail can verify them.
"""
from __future__ import annotations

import json
from typing import Any

from app import config

_PROMPT = """You are a music recommendation assistant. Using ONLY the songs below
(already retrieved for the user's request), recommend the best matches and briefly
explain why they fit.

Rules:
- Use ONLY these songs. NEVER invent songs, artists, or titles.
- Wrap each song's EXACT title in double quotes.
- Be friendly and concise: a sentence or two, then a short bullet list.

User request: {query}

Retrieved songs (JSON):
{songs}

Recommendation:"""


def _offline(query: str, songs: list[dict[str, Any]]) -> str:
    if not songs:
        return (
            "I couldn't find a good match in the catalog for that. "
            "Try describing a mood, genre, or activity (e.g. \"calm study music\")."
        )
    lines = ["Here are some songs that fit your request:"]
    for s in songs:
        bits = f'"{s["title"]}" by {s.get("artist", "unknown")}'
        detail = " ".join(x for x in (s.get("mood", ""), s.get("genre", "")) if x).strip()
        if detail:
            bits += f" — {detail}"
        if s.get("vibe"):
            bits += f", {s['vibe']} vibe"
        if s.get("final_score") is not None:
            bits += f" (match {s['final_score']:.2f})"
        lines.append(f"  • {bits}")
    return "\n".join(lines)


class OfflineGenerator:
    def generate(self, query: str, songs: list[dict[str, Any]]) -> str:
        return _offline(query, songs)


class GeminiGenerator:
    def __init__(self) -> None:
        import google.generativeai as genai  # lazy: only with a key

        genai.configure(api_key=config.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(config.GEMINI_MODEL)

    def generate(self, query: str, songs: list[dict[str, Any]]) -> str:
        if not songs:
            return _offline(query, songs)
        try:
            compact = [
                {k: s.get(k) for k in ("title", "artist", "genre", "mood", "vibe", "final_score")}
                for s in songs
            ]
            resp = self._model.generate_content(
                _PROMPT.format(query=query, songs=json.dumps(compact, indent=2)),
                request_options={"timeout": config.LLM_TIMEOUT_S},
            )
            return (getattr(resp, "text", "") or "").strip() or _offline(query, songs)
        except Exception:
            return _offline(query, songs)


def get_generator():
    """Return the active generator based on configuration."""
    return GeminiGenerator() if config.USE_LLM else OfflineGenerator()
