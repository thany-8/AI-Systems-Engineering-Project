"""Central configuration for the PawPal+ Companion agent app.

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
PAWPAL_DIR = ROOT / "module2-pawpal"                    # Module 2 engine
RECOMMENDER_DIR = ROOT / "module3-music-recommender"    # Module 3 engine
SONGS_CSV = RECOMMENDER_DIR / "data" / "songs.csv"
LOG_DIR = APP_DIR / "logs"

# ── LLM (Google Gemini, free tier) ───────────────────────────────────────
GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
).strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").strip()
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "30"))

# When no key is configured the agent runs a deterministic offline planner so
# the app is still fully functional and testable.
USE_LLM = bool(GEMINI_API_KEY)

# ── Agent guardrail limits ───────────────────────────────────────────────
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "2000"))
MAX_TOOL_CALLS = int(os.environ.get("MAX_TOOL_CALLS", "4"))   # per request
MAX_REPLANS = int(os.environ.get("MAX_REPLANS", "2"))         # revisions allowed


def llm_mode() -> str:
    """Return the active reasoning mode: 'gemini' or 'offline'."""
    return "gemini" if USE_LLM else "offline"
