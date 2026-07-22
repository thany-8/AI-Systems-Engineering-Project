"""Tests for the Music RAG Recommender.

Everything runs deterministically offline (no API key, no network): retrieval
and the vibe model are local, and generation uses the offline template or a
small fake generator.
"""
import pytest

from app import corpus, guardrails, pipeline, retriever, vibe_model


class _HallucinatingGenerator:
    """Generates an answer citing a song that was never retrieved."""

    def generate(self, query, songs):
        return 'You absolutely must hear "Totally Fake Song".'


# ── Corpus (RAG source) ────────────────────────────────────────────────────
def test_corpus_builds_documents():
    docs = corpus.load_documents()
    assert len(docs) == 30
    assert all(d.get("text") for d in docs)
    assert docs[0]["title"] in docs[0]["text"]  # description names the song


# ── Retrieval (RAG: Retrieve) ──────────────────────────────────────────────
def test_retriever_is_relevant():
    r = retriever.get_retriever()
    calm = [h["title"] for h in r.retrieve("calm music for studying", k=3)]
    assert {"Focus Flow", "Midnight Coding", "Library Rain"} & set(calm)

    sad = r.retrieve("sad rainy day", k=3)
    assert all("retrieval_score" in h for h in sad)
    assert "Someone Like You" in [h["title"] for h in sad]


# ── Specialized model ──────────────────────────────────────────────────────
def test_vibe_model_trains_predicts_and_evaluates():
    model = vibe_model.get_model()
    docs = corpus.load_documents()

    prediction = model.predict(docs[0])
    assert prediction in {"calm", "upbeat", "intense", "melancholy"}

    proba = model.predict_proba(docs[0])
    assert abs(sum(proba.values()) - 1.0) < 1e-6

    report = model.evaluate(docs)
    assert 0.0 <= report["cv_accuracy"] <= 1.0
    assert report["samples"] == 30


def test_vibe_of_mood_mapping():
    assert vibe_model.vibe_of_mood("happy") == "upbeat"
    assert vibe_model.vibe_of_mood("sad") == "melancholy"
    assert vibe_model.vibe_of_mood("something-unknown") == vibe_model.DEFAULT_VIBE


# ── Pipeline (retrieve → re-rank → generate → verify) ──────────────────────
def test_detect_vibe():
    assert pipeline.detect_vibe("calm study music") == "calm"
    assert pipeline.detect_vibe("sad rainy day songs") == "melancholy"
    assert pipeline.detect_vibe("purple monday chair") is None


def test_pipeline_reranks_and_is_grounded():
    out = pipeline.recommend("sad songs for a rainy day")
    assert out["results"]
    assert out["desired_vibe"] == "melancholy"
    # The trained model pushes a melancholy song to the top.
    assert out["results"][0]["vibe"] == "melancholy"
    titles = [r["title"] for r in out["results"]]
    assert guardrails.ungrounded_song_citations(out["answer"], titles) == []
    assert [s["step"] for s in out["trace"]] == ["retrieve", "rank", "guardrail"]


def test_pipeline_calm_query_top_is_calm():
    out = pipeline.recommend("calm music for studying")
    assert out["results"][0]["vibe"] == "calm"


def test_grounding_guardrail_replaces_hallucination():
    out = pipeline.recommend("calm study music", gen=_HallucinatingGenerator())
    assert any(s["step"] == "guardrail" and s.get("grounded") is False for s in out["trace"])
    titles = [r["title"] for r in out["results"]]
    assert guardrails.ungrounded_song_citations(out["answer"], titles) == []


# ── Guardrails ─────────────────────────────────────────────────────────────
def test_sanitize_input():
    with pytest.raises(guardrails.GuardrailError):
        guardrails.sanitize_input("   ")
    with pytest.raises(guardrails.GuardrailError):
        guardrails.sanitize_input("x" * 10000)
    assert guardrails.sanitize_input("  hi  ") == "hi"


# ── HTTP API ───────────────────────────────────────────────────────────────
def test_api_endpoints():
    from app.server import app as flask_app

    client = flask_app.test_client()
    assert client.get("/api/health").get_json()["status"] == "ok"

    ok = client.post("/api/recommend", json={"query": "calm study music"})
    assert ok.status_code == 200
    body = ok.get_json()
    assert body["answer"] and body["results"]

    bad = client.post("/api/recommend", json={"query": "   "})
    assert bad.status_code == 400
