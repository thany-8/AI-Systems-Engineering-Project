"""Central configuration for the Music RAG Recommender.

All tunables live here so behaviour is reproducible and easy to audit. Secrets
(the Gemini API key) are read from the environment / a local .env file and are
never hard-coded.
"""
from __future__ import annotations

import os
from pathlib import Path

# Load a local .env if present (optional dependency; safe if missing).
try:  # pragma: no cover - trivial
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent          # repo root
APP_DIR = Path(__file__).resolve().parent
RECOMMENDER_DIR = ROOT / "module3-music-recommender"    # Module 3 dataset + loader
SONGS_CSV = RECOMMENDER_DIR / "data" / "songs.csv"
LOG_DIR = APP_DIR / "logs"
MODEL_DIR = APP_DIR / "models"

# ── LLM (Google Gemini, free tier) ───────────────────────────────────────
GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
).strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").strip()
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "30"))

# When no key is configured, generation uses a deterministic offline template so
# the app is still fully functional and testable.
USE_LLM = bool(GEMINI_API_KEY)

# ── Web app: sessions + accounts database ────────────────────────────────
# Secret used to sign login-session cookies. A stable dev default keeps local
# runs working out of the box; set SECRET_KEY to a long random value in
# production so existing sessions can't be forged.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-in-production")
# Accounts and saved playlists live in a local SQLite file by default (free, no
# external setup). Override DATABASE_URL to point at another SQLAlchemy database.
DB_PATH = APP_DIR / "app.sqlite"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

# ── Guardrail limits ─────────────────────────────────────────────────────
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "2000"))

# ── Retrieval (RAG) + specialized model ──────────────────────────────────
RETRIEVAL_TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "5"))
VIBE_MODEL_PATH = MODEL_DIR / "vibe_model.joblib"
VIBE_RANDOM_STATE = 42
# Blend of lexical retrieval score and specialized-model vibe match in ranking.
RANK_RETRIEVAL_WEIGHT = 0.6
RANK_VIBE_WEIGHT = 0.4

# ── Semantic embeddings (optional upgrade over TF-IDF) ───────────────────
EMBED_MODEL = os.environ.get("EMBED_MODEL", "models/text-embedding-004")
DOC_EMBED_CACHE = MODEL_DIR / "doc_embeddings.joblib"
# Use Gemini embeddings for semantic retrieval when a key is available; the app
# falls back to TF-IDF otherwise (set USE_EMBEDDINGS=0 to force TF-IDF).
USE_EMBEDDINGS = USE_LLM and os.environ.get("USE_EMBEDDINGS", "1").lower() not in (
    "0", "false", "no",
)


def llm_mode() -> str:
    """Return the active reasoning mode: 'gemini' or 'offline'."""
    return "gemini" if USE_LLM else "offline"
