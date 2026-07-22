"""TF-IDF retrieval over the enriched song corpus — the *Retrieval* in RAG.

A lexical TF-IDF index keeps retrieval fully local, free, and deterministic (no
embeddings API, no heavyweight ML runtime). Given a free-text query we return
the most semantically-overlapping songs, which become the grounding context for
generation and the candidate set the specialized model re-ranks.
"""
from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import corpus


class Retriever:
    """Fit a TF-IDF index over song documents and retrieve by cosine similarity."""

    def __init__(self, documents: list[dict[str, Any]]):
        self.documents = documents
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(d["text"] for d in documents)

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Return the top-``k`` songs with a ``retrieval_score`` (0-1)."""
        vector = self.vectorizer.transform([query])
        sims = cosine_similarity(vector, self.matrix)[0]
        order = sims.argsort()[::-1][:k]
        results: list[dict[str, Any]] = []
        for i in order:
            song = dict(self.documents[i])
            song["retrieval_score"] = round(float(sims[i]), 4)
            results.append(song)
        return results


_RETRIEVER: Retriever | None = None


def get_retriever() -> Retriever:
    """Build (once) and return the shared retriever."""
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = Retriever(corpus.load_documents())
    return _RETRIEVER
