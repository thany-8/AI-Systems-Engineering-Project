"""The agentic loop: plan → act → check → (revise) → respond.

This is the core "agentic workflow": the agent plans which tools to call,
executes them, then *checks its own work* and may act again before composing a
grounded answer. Every step is logged and every tool call is guarded.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app import config, engines, guardrails, llm, tools


def _setup_logging() -> logging.Logger:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pawpal.agent")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler = logging.FileHandler(config.LOG_DIR / "agent.log")
        file_handler.setFormatter(fmt)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.propagate = False
    return logger


logger = _setup_logging()

_PLANNER: Any = None


def _default_planner() -> Any:
    global _PLANNER
    if _PLANNER is None:
        _PLANNER = llm.get_planner()
    return _PLANNER


def _execute(call: dict[str, Any], req_id: str) -> dict[str, Any]:
    """Run one validated tool call, capturing errors as observations."""
    name, args = call.get("name"), call.get("args") or {}
    try:
        result = tools.execute(name, args)
        logger.info("[%s] tool=%s args=%s -> ok", req_id, name, args)
        return {"tool": name, "args": args, "result": result}
    except guardrails.GuardrailError as exc:
        logger.warning("[%s] tool=%s blocked: %s", req_id, name, exc)
        return {"tool": name, "args": args, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[%s] tool=%s crashed", req_id, name)
        return {"tool": name, "args": args, "error": f"internal error: {exc}"}


def _followups(
    message: str, observations: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    """Deterministic self-check: inspect results and decide if more work helps.

    Returns ``(additional_tool_calls, reason)``. An empty list means the current
    results are good enough.
    """
    low = message.lower()
    wants_music = any(w in low for w in llm._MUSIC_WORDS)
    music_obs = [o for o in observations if o["tool"] == "recommend_music" and not o.get("error")]
    plan_obs = [o for o in observations if o["tool"] == "plan_pet_day" and not o.get("error")]

    # Rule 1 — user wanted music and we have a care plan but no music yet:
    # pick music that suits the longest activity in the plan.
    if wants_music and plan_obs and not music_obs:
        included = plan_obs[-1]["result"]["included"]
        if included:
            longest = max(included, key=lambda t: t["duration"])
            activity = longest["task_type"]
            if activity in engines.ACTIVITY_VIBES:
                return (
                    [{"name": "recommend_music", "args": {"activity": activity, "k": 3}}],
                    f"you also asked for music — matching it to your longest task ({activity})",
                )

    # Rule 2 — a constrained music query matched poorly: broaden it.
    for obs in music_obs:
        results, args = obs["result"], (obs.get("args") or {})
        constrained = "genre" in args or "mood" in args
        if results and constrained and max(r["score"] for r in results) < 0.35:
            relaxed = {k: v for k, v in args.items() if k in ("activity", "energy")}
            relaxed.setdefault("k", 3)
            already = any((o.get("args") or {}) == relaxed for o in music_obs)
            if not already:
                return (
                    [{"name": "recommend_music", "args": relaxed}],
                    "the first music match was weak — broadening the search",
                )

    return ([], "results are sufficient")


def _known_titles(observations: list[dict[str, Any]]) -> list[str]:
    titles: list[str] = []
    for obs in observations:
        if obs["tool"] == "recommend_music" and not obs.get("error"):
            titles.extend(r["title"] for r in obs["result"])
    return titles


def run(message: str, planner: Any | None = None) -> dict[str, Any]:
    """Handle one user turn end-to-end. Raises ``GuardrailError`` on bad input."""
    req_id = uuid.uuid4().hex[:8]
    started = time.time()
    text = guardrails.sanitize_input(message)
    planner = planner or _default_planner()
    trace: list[dict[str, Any]] = []
    logger.info("[%s] user=%r mode=%s", req_id, text[:200], config.llm_mode())

    # 1) PLAN
    decision = planner.plan(text)
    if decision.final and not decision.tool_calls:
        logger.info("[%s] plan=final (no tools)", req_id)
        trace.append({"step": "plan", "final": True})
        return _result(decision.final, trace, req_id, started, 0, 0)
    trace.append({"step": "plan", "tool_calls": [c["name"] for c in decision.tool_calls]})

    # 2) ACT + CHECK loop
    observations: list[dict[str, Any]] = []
    pending = list(decision.tool_calls)
    replans = 0
    while pending and len(observations) < config.MAX_TOOL_CALLS:
        obs = _execute(pending.pop(0), req_id)
        observations.append(obs)
        trace.append(
            {"step": "act", "tool": obs["tool"], "args": obs.get("args"),
             "ok": not obs.get("error"), "error": obs.get("error")}
        )
        if not pending and replans < config.MAX_REPLANS and len(observations) < config.MAX_TOOL_CALLS:
            extra, reason = _followups(text, observations)
            if extra:
                replans += 1
                pending.extend(extra)
                trace.append({"step": "check", "ok": False, "reason": reason,
                              "add": [c["name"] for c in extra]})
                logger.info("[%s] check -> revise: %s", req_id, reason)
    trace.append({"step": "check", "ok": True, "reason": "results are sufficient"})

    # 3) COMPOSE + grounding guardrail
    answer = planner.compose(text, observations)
    offending = guardrails.ungrounded_song_citations(answer, _known_titles(observations))
    if offending:
        logger.warning("[%s] ungrounded citations %s -> offline compose", req_id, offending)
        answer = llm.OfflinePlanner().compose(text, observations)
        trace.append({"step": "guardrail", "grounded": False, "offending": offending})
    else:
        trace.append({"step": "guardrail", "grounded": True})

    return _result(answer, trace, req_id, started, len(observations), replans)


def _result(answer, trace, req_id, started, tool_count, replans) -> dict[str, Any]:
    elapsed_ms = int((time.time() - started) * 1000)
    logger.info("[%s] done in %dms tools=%d replans=%d", req_id, elapsed_ms, tool_count, replans)
    return {
        "answer": answer,
        "trace": trace,
        "mode": config.llm_mode(),
        "request_id": req_id,
        "elapsed_ms": elapsed_ms,
    }
