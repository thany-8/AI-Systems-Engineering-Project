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

from app import config, generator, guardrails, personalize, retriever, vibe_model


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
    "energy", "valence", "retrieval_score", "final_score",
    "intensity_match", "personal_score", "personal_why",
)


def detect_vibe(query: str) -> str | None:
    """Infer the desired vibe from query keywords, or ``None`` if unclear."""
    low = query.lower()
    scores = {v: sum(1 for kw in kws if kw in low) for v, kws in _VIBE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


# ── Intensity nuance ───────────────────────────────────────────────────────
# Words that signal how *intense* (energetic) the user wants the music, mapped
# to a target ``energy`` in [0, 1]. Modifiers shift the target toward the
# extremes ("very") or the middle ("a bit"), and negation ("not too intense")
# pulls it back across the midpoint.
_INTENSITY_HIGH = (
    "high energy", "high-energy", "high intensity", "high octane", "intense",
    "hard", "heavy", "powerful", "hype", "banger", "aggressive", "pumping",
    "energetic", "adrenaline", "epic", "fast-paced", "fast", "pump", "party", "upbeat",
)
_INTENSITY_LOW = (
    "low energy", "low-energy", "low intensity", "mellow", "chill", "calm",
    "calming", "soft", "gentle", "relaxed", "relaxing", "quiet", "slow",
    "sleepy", "soothing", "ambient", "laid-back", "laidback", "downtempo",
    "lo-fi", "lofi",
)
_INTENSITY_AMP = ("very", "super", "really", "extremely", "insanely", "ultra")
_INTENSITY_SOFT = ("a bit", "slightly", "kinda", "kind of", "somewhat", "a little", "mildly", "fairly")
_INTENSITY_NEG = ("not too", "not very", "not so", "not that", "less ")


def _intensity_label(energy: float) -> str:
    return "high" if energy >= 0.66 else "low" if energy <= 0.4 else "medium"


def detect_intensity(query: str) -> dict[str, Any] | None:
    """Infer a desired intensity (target energy) from the query, or ``None``."""
    low = f" {query.lower()} "
    if " medium " in low or "moderate" in low:  # explicit middle wins
        return {"label": "medium", "energy": 0.5, "source": "query"}
    high = any(k in low for k in _INTENSITY_HIGH)
    quiet = any(k in low for k in _INTENSITY_LOW)
    if not (high or quiet):
        return None

    negate = any(k in low for k in _INTENSITY_NEG)
    amplify = any(k in low for k in _INTENSITY_AMP)
    soften = any(k in low for k in _INTENSITY_SOFT)

    if high and not quiet:
        energy = 0.45 if negate else 0.95 if amplify else 0.7 if soften else 0.85
    elif quiet and not high:
        energy = 0.55 if negate else 0.1 if amplify else 0.35 if soften else 0.2
    else:  # conflicting cues → aim for the middle
        energy = 0.5
    return {"label": _intensity_label(energy), "energy": round(energy, 2), "source": "query"}


def _coerce_energy(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return min(1.0, max(0.0, float(value)))
    text = str(value).strip().lower()
    labels = {"low": 0.2, "medium": 0.5, "med": 0.5, "high": 0.85}
    if text in labels:
        return labels[text]
    try:
        return min(1.0, max(0.0, float(text)))
    except ValueError:
        return None


def resolve_intensity(query: str, intensity: Any = None) -> dict[str, Any] | None:
    """Resolve intensity from an explicit override (UI) or from the query text."""
    if intensity is not None and intensity != "":
        energy = _coerce_energy(intensity)
        if energy is not None:
            return {
                "label": _intensity_label(energy),
                "energy": round(energy, 2),
                "source": "explicit",
            }
    return detect_intensity(query)


def _rerank(
    query: str,
    hits: list[dict[str, Any]],
    model: vibe_model.VibeModel,
    desired_energy: float | None = None,
    profile: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str | None, str]:
    """Blend retrieval score, the model's vibe match, requested intensity, and
    the user's taste profile. Intensity and personalization terms are only added
    when applicable, so with neither active the score is unchanged."""
    if not hits:
        return [], None, "none"
    desired = detect_vibe(query)
    source = "query"
    if desired is None:  # keep the model in the loop: cohere around the top hit
        desired = model.predict(hits[0])
        source = "inferred-from-top-hit"

    max_ret = max(h["retrieval_score"] for h in hits) or 1.0
    personalized = personalize.has_signal(profile)
    for h in hits:
        proba = model.predict_proba(h)
        predicted = max(proba, key=proba.get)
        h["vibe"] = predicted
        h["vibe_confidence"] = round(proba[predicted], 3)
        norm_retrieval = h["retrieval_score"] / max_ret
        vibe_match = proba.get(desired, 0.0)
        base = (
            config.RANK_RETRIEVAL_WEIGHT * norm_retrieval
            + config.RANK_VIBE_WEIGHT * vibe_match
        )
        if desired_energy is not None:
            intensity_match = 1.0 - abs(float(h.get("energy", 0.5)) - desired_energy)
            h["intensity_match"] = round(intensity_match, 3)
            score = (
                (1 - config.RANK_INTENSITY_WEIGHT) * base
                + config.RANK_INTENSITY_WEIGHT * intensity_match
            )
        else:
            score = base
        if personalized:
            personal = personalize.score(h, profile)
            h["personal_score"] = round(personal, 3)
            why = personalize.explain(h, profile)
            if why:
                h["personal_why"] = why
            score += config.RANK_PERSONALIZATION_WEIGHT * personal
        h["final_score"] = round(score, 4)
    ranked = sorted(hits, key=lambda s: s["final_score"], reverse=True)
    return ranked, desired, source


def _public(song: dict[str, Any]) -> dict[str, Any]:
    return {k: song.get(k) for k in _PUBLIC_FIELDS}


def recommend(
    query: str, *, retr=None, model=None, gen=None, user_profile=None, intensity=None
) -> dict[str, Any]:
    """Run the full RAG pipeline. Raises ``GuardrailError`` on bad input."""
    req_id = uuid.uuid4().hex[:8]
    started = time.time()
    text = guardrails.sanitize_input(query)
    retr = retr or retriever.get_retriever()
    model = model or vibe_model.get_model()
    gen = gen or generator.get_generator()
    intensity_info = resolve_intensity(text, intensity)
    desired_energy = intensity_info["energy"] if intensity_info else None
    personalized = personalize.has_signal(user_profile)
    trace: list[dict[str, Any]] = []
    logger.info("[%s] query=%r mode=%s", req_id, text[:200], config.llm_mode())

    # 1) RETRIEVE (a larger pool when intensity/personalization can re-order it)
    pool_k = (
        config.RERANK_POOL_K
        if (desired_energy is not None or personalized)
        else config.RETRIEVAL_TOP_K
    )
    hits = retr.retrieve(text, k=pool_k)
    method = getattr(retr, "name", "tfidf")
    trace.append({
        "step": "retrieve",
        "method": method,
        "k": pool_k,
        "hits": [{"title": h["title"], "score": h["retrieval_score"]} for h in hits],
    })
    logger.info(
        "[%s] retrieved=%d via=%s top=%s",
        req_id, len(hits), method, hits[0]["title"] if hits else None,
    )

    # 2) RE-RANK with the specialized model, then trim to the display size
    ranked, desired, source = _rerank(
        text, hits, model, desired_energy=desired_energy, profile=user_profile
    )
    ranked = ranked[: config.RETRIEVAL_TOP_K]
    trace.append({
        "step": "rank",
        "desired_vibe": desired,
        "desired_intensity": intensity_info["label"] if intensity_info else None,
        "personalized": personalized,
        "source": source,
        "order": [
            {"title": h["title"], "vibe": h["vibe"], "final_score": h["final_score"]}
            for h in ranked
        ],
    })
    logger.info("[%s] reranked desired=%s (%s)", req_id, desired, source)

    # 3) GENERATE (grounded). On a suspected prompt injection, skip the LLM
    # entirely and use the deterministic offline template so the untrusted text
    # never reaches the model.
    if guardrails.looks_like_injection(text):
        logger.warning("[%s] suspected prompt injection; using offline generation", req_id)
        trace.append({"step": "input_guard", "injection_suspected": True})
        answer = generator.OfflineGenerator().generate(text, ranked)
    else:
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
        "desired_intensity": intensity_info,
        "personalized": personalized,
        "personalization": {
            "applied": personalized,
            "reactions": (user_profile or {}).get("likes", 0)
            + (user_profile or {}).get("dislikes", 0),
            "saved_playlists": (user_profile or {}).get("saved_playlists", 0),
        },
        "request_id": req_id,
        "elapsed_ms": elapsed,
    }
