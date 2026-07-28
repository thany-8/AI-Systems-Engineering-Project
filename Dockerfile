# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DATABASE_URL=sqlite:////app/data/app.sqlite

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY . .

# Pre-train the vibe model at build time so the first request is fast
# (the artifact is baked into the image rather than trained on first hit).
RUN python -m app.vibe_model

# Runtime data dir for the SQLite DB (mount a volume here to persist it) and a
# non-root user to run as.
RUN mkdir -p /app/data \
    && useradd --create-home appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.server:app"]
