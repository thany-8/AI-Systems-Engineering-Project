"""Tests for the PawPal+ Companion agent.

All tests run deterministically in offline mode (no API key, no network) by
using ``OfflinePlanner`` or small fake planners, so they are fully reproducible.
"""
import pytest

from app import agent, engines, guardrails, tools
from app.llm import Decision, OfflinePlanner


# ── Fake planners for targeted agent tests ────────────────────────────────
class ScheduleOnlyPlanner:
    """Plans only a schedule, so the agent's self-check must add the music."""

    def plan(self, message):
        return Decision(tool_calls=[{"name": "plan_pet_day", "args": {"available_minutes": 60}}])

    def compose(self, message, observations):
        return OfflinePlanner().compose(message, observations)


class HallucinatingPlanner:
    """Composes an answer citing a song that was never retrieved."""

    def plan(self, message):
        return Decision(tool_calls=[{"name": "recommend_music", "args": {"activity": "grooming"}}])

    def compose(self, message, observations):
        return 'You should absolutely hear "Totally Fake Song" right now.'


def _acts(result):
    return [s["tool"] for s in result["trace"] if s["step"] == "act"]


# ── Engines ────────────────────────────────────────────────────────────────
def test_plan_pet_day_respects_time_budget():
    plan = engines.plan_pet_day(available_minutes=25)
    assert plan["total_minutes"] <= 25
    assert plan["included"], "at least one task should fit in 25 minutes"
    # High-priority work is scheduled first.
    assert plan["included"][0]["priority"] == "high"


def test_recommend_music_is_grounded_in_catalog():
    catalog_titles = {s["title"] for s in engines.get_catalog()}
    recs = engines.recommend_music(activity="grooming", k=3)
    assert recs
    assert all(r["title"] in catalog_titles for r in recs)


def test_list_pets_and_tasks():
    data = engines.list_pets_and_tasks()
    assert set(data["pets"]) == {"Max", "Luna"}


# ── Guardrails ───────────────────────────────────────────────────────────
def test_sanitize_input_rejects_empty_and_oversized():
    with pytest.raises(guardrails.GuardrailError):
        guardrails.sanitize_input("   ")
    with pytest.raises(guardrails.GuardrailError):
        guardrails.sanitize_input("x" * 10000)
    assert guardrails.sanitize_input("  hi  ") == "hi"


def test_tool_validation_blocks_bad_calls():
    with pytest.raises(guardrails.GuardrailError):
        tools.execute("does_not_exist", {})
    with pytest.raises(guardrails.GuardrailError):
        tools.execute("recommend_music", {"energy": 5})       # out of range
    with pytest.raises(guardrails.GuardrailError):
        tools.execute("recommend_music", {"unknown": 1})      # unknown arg
    with pytest.raises(guardrails.GuardrailError):
        tools.execute("plan_pet_day", {"available_minutes": "lots"})  # bad type
    assert tools.execute("recommend_music", {"activity": "walk", "k": 2})


def test_ungrounded_song_citations():
    assert guardrails.ungrounded_song_citations('play "Fake Title"', ["Despacito"]) == ["Fake Title"]
    assert guardrails.ungrounded_song_citations('play "Despacito"', ["Despacito"]) == []


# ── Agent routing ────────────────────────────────────────────────────────
def test_agent_routes_music_only():
    out = agent.run("calm songs for grooming", planner=OfflinePlanner())
    assert _acts(out) == ["recommend_music"]


def test_agent_routes_schedule_only():
    out = agent.run("plan my day, I have 45 minutes", planner=OfflinePlanner())
    acts = _acts(out)
    assert "plan_pet_day" in acts and "recommend_music" not in acts


def test_agent_handles_combined_request():
    out = agent.run("plan my day and play music, 60 minutes", planner=OfflinePlanner())
    acts = _acts(out)
    assert "plan_pet_day" in acts and "recommend_music" in acts


def test_agent_returns_help_without_tools():
    out = agent.run("hi, what can you do?", planner=OfflinePlanner())
    assert any(s.get("final") for s in out["trace"])
    assert "PawPal+" in out["answer"]


# ── Agentic self-check (plan → act → check → act) ──────────────────────────
def test_self_check_adds_music_after_plan():
    out = agent.run("plan my day and add music, 60 minutes", planner=ScheduleOnlyPlanner())
    assert any(s["step"] == "check" and s["ok"] is False for s in out["trace"])
    assert _acts(out) == ["plan_pet_day", "recommend_music"]


def test_followups_broaden_weak_match():
    weak = [{
        "tool": "recommend_music",
        "args": {"genre": "ambient", "mood": "party"},
        "result": [{"title": "X", "score": 0.1}],
    }]
    calls, reason = agent._followups("party ambient music", weak)
    assert calls and calls[0]["name"] == "recommend_music"
    assert "genre" not in calls[0]["args"] and "mood" not in calls[0]["args"]


def test_followups_satisfied_on_strong_match():
    strong = [{
        "tool": "recommend_music",
        "args": {"genre": "reggaeton"},
        "result": [{"title": "Despacito", "score": 0.96}],
    }]
    calls, _ = agent._followups("reggaeton", strong)
    assert calls == []


# ── Output grounding guardrail ─────────────────────────────────────────────
def test_grounding_guardrail_replaces_hallucination():
    out = agent.run("music for grooming", planner=HallucinatingPlanner())
    assert any(s["step"] == "guardrail" and s.get("grounded") is False for s in out["trace"])
    catalog_titles = [s["title"] for s in engines.get_catalog()]
    assert guardrails.ungrounded_song_citations(out["answer"], catalog_titles) == []


# ── HTTP API ───────────────────────────────────────────────────────────────
def test_api_endpoints():
    from app.server import app as flask_app

    client = flask_app.test_client()
    assert client.get("/api/health").get_json()["status"] == "ok"

    ok = client.post("/api/chat", json={"message": "calm songs for grooming"})
    assert ok.status_code == 200 and ok.get_json()["answer"]

    bad = client.post("/api/chat", json={"message": "   "})
    assert bad.status_code == 400
