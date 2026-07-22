"""RAG pipeline: retrieve → specialized-model re-rank → generate → verify.

This replaces the earlier agent loop. One request flows through:

1. **Retrieve** relevant songs from the enriched corpus (TF-IDF).
2. **Re-rank** them with the trained *vibe* classifier, blending lexical
   relevance with how well each candidate matches the desired vibe.
3. **Generate** a grounded recommendation from the ranked songs.
4. **Verify** the answer cites only retrieved songs (grounding guardrail).

Every stage is logged and returned as a ``trace`` for transparency.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app import config, generator, guardrails, retriever, vibe_model


def _setup_logging() -> logging.Logger:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("music.pipeline")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler = logging.FileHandler(config.LOG_DIR / "app.log")
        file_handler.setFormatter(fmt)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.propagate = False
    return logger


logger = _setup_logging()

# Keywords that signal a desired vibe in the user's request.
_VIBE_KEYWORDS = {
    "calm": ["calm", "chill", "relax", "study", "focus", "sleep", "soft", "mellow", "coffee", "acoustic"],
    "upbeat": ["happy", "upbeat", "party", "dance", "fun", "feel good", "summer", "workout", "gym", "energetic"],
    "intense": ["intense", "hard", "powerful", "heavy", "pump", "aggressive", "epic"],
    "melancholy": ["sad", "melancholy", "rainy", "heartbreak", "cry", "emotional", "breakup", "moody", "dark", "lonely"],
}

_PUBLIC_FIELDS = (
    "title", "artist", "genre", "mood", "vibe", "vibe_confidence",
    "retrieval_score", "final_score",
)


def detect_vibe(query: str) -> str | None:
    """Infer the desired vibe from query keywords, or ``None`` if unclear."""
    low = query.lower()
    scores = {v: sum(1 for kw in kws if kw in low) for v, kws in _VIBE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def _rerank(
    query: str, hits: list[dict[str, Any]], model: vibe_model.VibeModel
) -> tuple[list[dict[str, Any]], str | None, str]:
    """Blend retrieval score with the specialized model's vibe match."""
    if not hits:
        return [], None, "none"
    desired = detect_vibe(query)
    source = "query"
    if desired is None:  # keep the model in the loop: cohere around the top hit
        desired = model.predict(hits[0])
        source = "inferred-from-top-hit"

    max_ret = max(h["retrieval_score"] for h in hits) or 1.0
    for h in hits:
        proba = model.predict_proba(h)
        predicted = max(proba, key=proba.get)
        h["vibe"] = predicted
        h["vibe_confidence"] = round(proba[predicted], 3)
        norm_retrieval = h["retrieval_score"] / max_ret
        vibe_match = proba.get(desired, 0.0)
        h["final_score"] = round(
            config.RANK_RETRIEVAL_WEIGHT * norm_retrieval
            + config.RANK_VIBE_WEIGHT * vibe_match,
            4,
        )
    ranked = sorted(hits, key=lambda s: s["final_score"], reverse=True)
    return ranked, desired, source


def _public(song: dict[str, Any]) -> dict[str, Any]:
    return {k: song.get(k) for k in _PUBLIC_FIELDS}


def recommend(
    query: str, *, retr=None, model=None, gen=None
) -> dict[str, Any]:
    """Run the full RAG pipeline. Raises ``GuardrailError`` on bad input."""
    req_id = uuid.uuid4().hex[:8]
    started = time.time()
    text = guardrails.sanitize_input(query)
    retr = retr or retriever.get_retriever()
    model = model or vibe_model.get_model()
    gen = gen or generator.get_generator()
    trace: list[dict[str, Any]] = []
    logger.info("[%s] query=%r mode=%s", req_id, text[:200], config.llm_mode())

    # 1) RETRIEVE
    hits = retr.retrieve(text, k=config.RETRIEVAL_TOP_K)
    trace.append({
        "step": "retrieve",
        "k": config.RETRIEVAL_TOP_K,
        "hits": [{"title": h["title"], "score": h["retrieval_score"]} for h in hits],
    })
    logger.info("[%s] retrieved=%d top=%s", req_id, len(hits), hits[0]["title"] if hits else None)

    # 2) RE-RANK with the specialized model
    ranked, desired, source = _rerank(text, hits, model)
    trace.append({
        "step": "rank",
        "desired_vibe": desired,
        "source": source,
        "order": [
            {"title": h["title"], "vibe": h["vibe"], "final_score": h["final_score"]}
            for h in ranked
        ],
    })
    logger.info("[%s] reranked desired=%s (%s)", req_id, desired, source)

    # 3) GENERATE (grounded)
    answer = gen.generate(text, ranked)

    # 4) VERIFY grounding
    offending = guardrails.ungrounded_song_citations(answer, [h["title"] for h in ranked])
    if offending:
        logger.warning("[%s] ungrounded citations %s -> offline generation", req_id, offending)
        answer = generator.OfflineGenerator().generate(text, ranked)
        trace.append({"step": "guardrail", "grounded": False, "offending": offending})
    else:
        trace.append({"step": "guardrail", "grounded": True})

    elapsed = int((time.time() - started) * 1000)
    logger.info("[%s] done in %dms", req_id, elapsed)
    return {
        "answer": answer,
        "results": [_public(h) for h in ranked],
        "trace": trace,
        "mode": config.llm_mode(),
        "desired_vibe": desired,
        "request_id": req_id,
        "elapsed_ms": elapsed,
    }
