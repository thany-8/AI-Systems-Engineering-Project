"""Google Gemini text embeddings (free tier) for semantic retrieval.

Kept behind a small function boundary so the retriever can fall back to TF-IDF
when no API key is configured or the embedding API is unavailable.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np

from app import config


class EmbeddingError(Exception):
    """Raised when embeddings cannot be produced."""


def _configure():
    import google.generativeai as genai  # lazy: only needed with a key

    genai.configure(api_key=config.GEMINI_API_KEY)
    return genai


def embed_texts(texts: Iterable[str], *, task_type: str = "retrieval_document") -> np.ndarray:
    """Embed a list of texts, returning an ``(n, d)`` float32 matrix."""
    if not config.GEMINI_API_KEY:
        raise EmbeddingError("no GEMINI_API_KEY configured")
    genai = _configure()
    try:
        resp = genai.embed_content(
            model=config.EMBED_MODEL, content=list(texts), task_type=task_type
        )
        vectors = resp["embedding"]
    except Exception as exc:  # network / quota / bad model → caller falls back
        raise EmbeddingError(str(exc)) from exc

    arr = np.asarray(vectors, dtype="float32")
    if arr.ndim == 1:  # single vector returned for a one-item batch
        arr = arr.reshape(1, -1)
    return arr


def embed_query(text: str) -> np.ndarray:
    """Embed a single query string, returning a 1-D float32 vector."""
    return embed_texts([text], task_type="retrieval_query")[0]
