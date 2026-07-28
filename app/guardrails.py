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


# Control characters don't belong in a short free-text mood query and can be used
# to smuggle newline-based role spoofing / prompt-injection payloads.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")

# Best-effort detection of prompt-injection / jailbreak attempts in the query.
# Defense-in-depth: on a match the pipeline skips the LLM and uses the
# deterministic offline generator, and output grounding still runs — so a false
# positive only costs nicer prose, never safety.
_INJECTION = re.compile(
    r"""(?ix)
    (?:
        ignore\s+(?:all\s+|any\s+|the\s+)*(?:previous|prior|above|earlier|preceding)\s+(?:instruction|instructions|prompt|prompts|rule|rules|message|messages)
      | disregard\s+(?:all\s+|any\s+|the\s+)*(?:previous|prior|above|earlier|instruction|instructions|rule|rules)
      | forget\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instruction|instructions|prompt|prompts)
      | you\s+are\s+now | you\s+are\s+no\s+longer | pretend\s+to\s+be
      | act\s+as\s+(?:a|an|if) | roleplay\s+as | behave\s+like
      | (?:system|developer|assistant)\s+(?:prompt|message|instructions?)
      | (?:reveal|expose|print|show|repeat|leak)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)
      | prompt\s+injection
      | <\s*/?\s*(?:system|assistant|user|im_start|im_end)\s*>
      | \[\s*/?\s*(?:inst|system|assistant)\s*\]
    )
    """,
)


def sanitize_input(message: Any) -> str:
    """Return a cleaned user query or raise ``GuardrailError``.

    Strips control characters and collapses whitespace so newline-based role
    spoofing can't be smuggled in, then enforces non-empty and max length.
    """
    if not isinstance(message, str):
        raise GuardrailError("query must be a string")
    text = _CONTROL_CHARS.sub(" ", message)
    text = _WHITESPACE.sub(" ", text).strip()
    if not text:
        raise GuardrailError("query must not be empty")
    if len(text) > config.MAX_INPUT_CHARS:
        raise GuardrailError(f"query too long (max {config.MAX_INPUT_CHARS} characters)")
    return text


def looks_like_injection(text: Any) -> bool:
    """True if the query resembles a prompt-injection / jailbreak attempt."""
    return bool(_INJECTION.search(text)) if isinstance(text, str) else False


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
