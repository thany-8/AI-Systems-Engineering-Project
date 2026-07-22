"""Guardrails: validate everything entering and leaving the agent.

These checks keep the agent safe and predictable:
* ``sanitize_input``      — reject empty / oversized user messages.
* ``validate_tool_call``  — enforce the tool allow-list, reject unknown
                            arguments, coerce types, and range-check values.
* ``ungrounded_song_citations`` — catch song titles the model invented that
                            were never returned by a tool (grounding).
"""
from __future__ import annotations

import re
from typing import Any

from app import config


class GuardrailError(Exception):
    """Raised when a request or tool call violates a guardrail."""


def sanitize_input(message: Any) -> str:
    """Return a cleaned user message or raise ``GuardrailError``."""
    if not isinstance(message, str):
        raise GuardrailError("message must be a string")
    text = message.strip()
    if not text:
        raise GuardrailError("message must not be empty")
    if len(text) > config.MAX_INPUT_CHARS:
        raise GuardrailError(
            f"message too long (max {config.MAX_INPUT_CHARS} characters)"
        )
    return text


def _coerce(tool: str, name: str, value: Any, spec: dict[str, Any]) -> Any:
    kind = spec["type"]
    try:
        if kind == "integer":
            coerced: Any = int(value)
        elif kind == "number":
            coerced = float(value)
        elif kind == "boolean":
            coerced = (
                value
                if isinstance(value, bool)
                else str(value).strip().lower() in ("true", "1", "yes")
            )
        elif kind == "string":
            coerced = str(value)
        else:  # pragma: no cover - defensive
            coerced = value
    except (TypeError, ValueError):
        raise GuardrailError(f"argument '{name}' for '{tool}' must be a {kind}")

    if "enum" in spec and coerced not in spec["enum"]:
        raise GuardrailError(
            f"argument '{name}' for '{tool}' must be one of {spec['enum']}"
        )
    if "min" in spec and coerced < spec["min"]:
        raise GuardrailError(f"argument '{name}' for '{tool}' must be >= {spec['min']}")
    if "max" in spec and coerced > spec["max"]:
        raise GuardrailError(f"argument '{name}' for '{tool}' must be <= {spec['max']}")
    return coerced


def validate_tool_call(
    name: Any, args: Any, registry: dict[str, Any]
) -> dict[str, Any]:
    """Validate ``args`` for tool ``name`` against ``registry``.

    Returns a cleaned, type-coerced argument dict. Raises ``GuardrailError`` for
    unknown tools, unknown arguments, wrong types, or out-of-range values.
    """
    if name not in registry:
        raise GuardrailError(f"unknown tool '{name}'")
    if not isinstance(args, dict):
        raise GuardrailError(f"arguments for '{name}' must be an object")

    params: dict[str, Any] = registry[name]["parameters"]
    for key in args:
        if key not in params:
            raise GuardrailError(f"unknown argument '{key}' for tool '{name}'")

    clean: dict[str, Any] = {}
    for pname, pspec in params.items():
        if pname in args and args[pname] is not None:
            clean[pname] = _coerce(name, pname, args[pname], pspec)
    return clean


# ── Output grounding ──────────────────────────────────────────────────────
_QUOTED = re.compile(r'"([^"]{2,80})"')


def ungrounded_song_citations(answer: str, known_titles: Any) -> list[str]:
    """Return quoted song titles in ``answer`` that were not actually retrieved.

    The composer is instructed to wrap every cited song title in double quotes,
    so any quoted phrase that is not among the retrieved titles is treated as a
    hallucination and reported here.
    """
    known = {str(t).lower() for t in known_titles}
    return [span for span in _QUOTED.findall(answer or "") if span.lower() not in known]
