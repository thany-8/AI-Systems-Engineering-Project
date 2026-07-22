"""Retrieval for RAG.

Two interchangeable retrievers share the same interface (``retrieve(query, k)``
returning songs with a ``retrieval_score``):

* :class:`EmbeddingRetriever` — semantic dense-vector search via Gemini
  embeddings (matches by *meaning*).
* :class:`Retriever` — lexical TF-IDF search, fully local and deterministic.

``get_retriever()`` prefers embeddings when a Gemini key is available and the
API works, and otherwise falls back to TF-IDF, so the app always runs.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import config, corpus, embeddings

logger = logging.getLogger("music.pipeline")


class Retriever:
    """Lexical TF-IDF retrieval — the local, deterministic fallback."""

    name = "tfidf"

    def __init__(self, documents: list[dict[str, Any]]):
        self.documents = documents
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(d["text"] for d in documents)

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        vector = self.vectorizer.transform([query])
        sims = cosine_similarity(vector, self.matrix)[0]
        return _top_k(self.documents, sims, k)


class EmbeddingRetriever:
    """Semantic retrieval over pre-computed, normalized document embeddings."""

    name = "embedding"

    def __init__(
        self,
        documents: list[dict[str, Any]],
        doc_matrix: np.ndarray,
        embed_query_fn: Callable[[str], np.ndarray],
    ):
        self.documents = documents
        self.matrix = doc_matrix  # rows are L2-normalized
        self._embed_query = embed_query_fn

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        q = np.asarray(self._embed_query(query), dtype="float32")
        norm = float(np.linalg.norm(q)) or 1.0
        sims = self.matrix @ (q / norm)  # cosine (rows already normalized)
        return _top_k(self.documents, sims, k)


def _top_k(documents: list[dict[str, Any]], sims, k: int) -> list[dict[str, Any]]:
    order = np.asarray(sims).argsort()[::-1][:k]
    results: list[dict[str, Any]] = []
    for i in order:
        song = dict(documents[int(i)])
        song["retrieval_score"] = round(float(sims[int(i)]), 4)
        results.append(song)
    return results


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _cache_key(documents: list[dict[str, Any]]) -> str:
    payload = config.EMBED_MODEL + "\n" + "\n".join(d["text"] for d in documents)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _load_or_build_doc_matrix(documents: list[dict[str, Any]]) -> np.ndarray:
    """Return normalized document embeddings, cached to disk by content hash."""
    key = _cache_key(documents)
    path = config.DOC_EMBED_CACHE
    if path.exists():
        try:
            cached = joblib.load(path)
            if cached.get("key") == key:
                return cached["matrix"]
        except Exception:  # pragma: no cover - stale/incompatible cache
            pass
    raw = embeddings.embed_texts([d["text"] for d in documents], task_type="retrieval_document")
    matrix = _normalize_rows(np.asarray(raw, dtype="float32"))
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"key": key, "matrix": matrix}, path)
    return matrix


def build_retriever():
    """Build the best available retriever (embeddings, else TF-IDF)."""
    documents = corpus.load_documents()
    if config.USE_EMBEDDINGS:
        try:
            matrix = _load_or_build_doc_matrix(documents)
            logger.info("retriever=embedding model=%s", config.EMBED_MODEL)
            return EmbeddingRetriever(documents, matrix, embeddings.embed_query)
        except Exception as exc:
            logger.warning("embedding retriever unavailable (%s); using TF-IDF", exc)
    return Retriever(documents)


_RETRIEVER = None


def get_retriever():
    """Build (once) and return the shared retriever."""
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = build_retriever()
    return _RETRIEVER
