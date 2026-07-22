"""Entrypoint: start the Music RAG Recommender web app.

Usage:
    python run.py            # serves http://127.0.0.1:5000
    PORT=8000 python run.py  # custom port
"""
from __future__ import annotations

import os

from app import config
from app.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(
        f"Music RAG Recommender — reasoning mode: {config.llm_mode()}  "
        f"→  http://127.0.0.1:{port}"
    )
    app.run(host="127.0.0.1", port=port, debug=False)
