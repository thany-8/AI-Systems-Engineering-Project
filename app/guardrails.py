"""Guardrails: validate what enters and leaves the pipeline.

* ``sanitize_input``            — reject empty / oversized user queries.
* ``ungrounded_song_citations`` — catch song titles the model invented that were
                                  never retrieved (output grounding for RAG).
"""
from __future__ import annotations

import re
from typing import Any

from app import config


class GuardrailError(Exception):
    """Raised when a request violates a guardrail."""


def sanitize_input(message: Any) -> str:
    """Return a cleaned user query or raise ``GuardrailError``."""
    if not isinstance(message, str):
        raise GuardrailError("query must be a string")
    text = message.strip()
    if not text:
        raise GuardrailError("query must not be empty")
    if len(text) > config.MAX_INPUT_CHARS:
        raise GuardrailError(f"query too long (max {config.MAX_INPUT_CHARS} characters)")
    return text


# ── Output grounding ──────────────────────────────────────────────────────
_QUOTED = re.compile(r'"([^"]{2,80})"')


def ungrounded_song_citations(answer: str, known_titles: Any) -> list[str]:
    """Return quoted song titles in ``answer`` that were not actually retrieved.

    The generator is instructed to wrap every cited song title in double quotes,
    so any quoted phrase not among the retrieved titles is treated as a
    hallucination and reported here.
    """
    known = {str(t).lower() for t in known_titles}
    return [span for span in _QUOTED.findall(answer or "") if span.lower() not in known]
