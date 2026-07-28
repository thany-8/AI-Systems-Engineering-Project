"""Gunicorn configuration for the AI Playlist Generator.

Run locally:  gunicorn --config gunicorn.conf.py app.server:app
(The Docker image uses this by default.)

Notes:
- ``preload_app`` imports the app once in the master so ``db.create_all()`` runs
  a single time — otherwise multiple workers race to create the schema on first
  boot. ``post_fork`` then disposes each worker's inherited DB engine so every
  worker opens its own connections (safe across the fork).
- With more than one worker, set RATELIMIT_STORAGE_URI to a shared Redis URL so
  rate limits are enforced globally rather than per-worker.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
graceful_timeout = 30
keepalive = 5
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")


def post_fork(server, worker):
    """Give each worker its own DB connections instead of sharing the master's."""
    from app.extensions import db
    from app.server import app

    with app.app_context():
        db.engine.dispose()

