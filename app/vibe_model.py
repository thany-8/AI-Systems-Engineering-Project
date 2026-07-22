"""Specialized model: a scikit-learn classifier trained to predict a song's
"vibe" from its audio features.

This is the project's *specialized / trained model*. The Module 3 catalog has
~20 free-text moods; we group them into four vibes and train a LogisticRegression
on the numeric audio features (energy, tempo, valence, danceability,
acousticness). The trained model then predicts a vibe (with confidence) for each
retrieved candidate, and the pipeline uses that to re-rank results — so the model
directly changes which songs surface.

Run ``python -m app.vibe_model`` to (re)train and print a cross-validated score.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import joblib
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app import config, corpus

FEATURES = ["energy", "tempo_bpm", "valence", "danceability", "acousticness"]

# Group the catalog's many moods into four learnable "vibes".
MOOD_TO_VIBE = {
    "happy": "upbeat", "party": "upbeat", "energetic": "upbeat",
    "playful": "upbeat", "confident": "upbeat", "flirty": "upbeat",
    "chill": "calm", "relaxed": "calm", "focused": "calm",
    "calm": "calm", "romantic": "calm",
    "intense": "intense", "powerful": "intense",
    "sad": "melancholy", "moody": "melancholy", "dark": "melancholy",
    "emotional": "melancholy",
}
DEFAULT_VIBE = "calm"


def vibe_of_mood(mood: str) -> str:
    return MOOD_TO_VIBE.get(str(mood).lower().strip(), DEFAULT_VIBE)


def _features(song: dict[str, Any]) -> list[float]:
    return [float(song[f]) for f in FEATURES]


class VibeModel:
    """A thin wrapper around a fitted scikit-learn pipeline."""

    def __init__(self, pipeline: Any, classes: list[str]):
        self.pipeline = pipeline
        self.classes = classes

    @classmethod
    def train(cls, songs: list[dict[str, Any]]) -> "VibeModel":
        X = [_features(s) for s in songs]
        y = [vibe_of_mood(s["mood"]) for s in songs]
        pipeline = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=config.VIBE_RANDOM_STATE),
        )
        pipeline.fit(X, y)
        return cls(pipeline, sorted(set(y)))

    def predict(self, song: dict[str, Any]) -> str:
        return str(self.pipeline.predict([_features(song)])[0])

    def predict_proba(self, song: dict[str, Any]) -> dict[str, float]:
        probs = self.pipeline.predict_proba([_features(song)])[0]
        return {str(cls): float(p) for cls, p in zip(self.pipeline.classes_, probs)}

    def evaluate(self, songs: list[dict[str, Any]]) -> dict[str, Any]:
        X = [_features(s) for s in songs]
        y = [vibe_of_mood(s["mood"]) for s in songs]
        counts = Counter(y)
        n_splits = max(2, min(5, min(counts.values())))
        skf = StratifiedKFold(
            n_splits=n_splits, shuffle=True, random_state=config.VIBE_RANDOM_STATE
        )
        scores = cross_val_score(clone(self.pipeline), X, y, cv=skf)
        return {
            "cv_accuracy": round(float(scores.mean()), 3),
            "cv_folds": n_splits,
            "samples": len(y),
            "class_distribution": dict(counts),
        }


_MODEL: VibeModel | None = None


def get_model(retrain: bool = False) -> VibeModel:
    """Return the shared model, loading from disk or training + caching it."""
    global _MODEL
    if _MODEL is not None and not retrain:
        return _MODEL
    if config.VIBE_MODEL_PATH.exists() and not retrain:
        try:
            _MODEL = joblib.load(config.VIBE_MODEL_PATH)
            return _MODEL
        except Exception:  # pragma: no cover - stale/incompatible cache
            pass
    _MODEL = VibeModel.train(corpus.load_documents())
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(_MODEL, config.VIBE_MODEL_PATH)
    return _MODEL


if __name__ == "__main__":  # pragma: no cover
    model = get_model(retrain=True)
    print("Trained vibe model →", config.VIBE_MODEL_PATH)
    print("Evaluation:", model.evaluate(corpus.load_documents()))
