# Applied AI System Project — Music RAG Recommender

A music recommender you talk to in plain language. It **retrieves** matching songs from a
local catalog (**RAG**), **re-ranks** them with a **trained scikit-learn "vibe" model**, and
**generates** a friendly, grounded explanation of the picks. It evolves my earlier **AI-110**
Module 3 recommender into an applied AI system with two advanced features.

![Architecture](assets/architecture.png)

> Generation **and semantic retrieval** use **Google Gemini** (free tier) when a key is set.
> Without a key the app uses a **deterministic offline template** for generation and a local
> **TF-IDF** retriever — so it always runs and is fully testable. The vibe model is always local.

## Two advanced AI features

**1. Retrieval-Augmented Generation (RAG).** Structured songs from `songs.csv` are turned into
natural-language description documents ([`app/corpus.py`](app/corpus.py)). A retriever
([`app/retriever.py`](app/retriever.py)) finds the songs most relevant to your request — using
**semantic Gemini embeddings** ([`app/embeddings.py`](app/embeddings.py)) when a key is set, and
a local **TF-IDF** index otherwise — and the generator answers **using only those retrieved
songs**: the retrieved data drives the response, and invented titles are rejected by a grounding
guardrail. Document embeddings are computed once and cached to `app/models/`.

**2. Specialized / trained model.** A scikit-learn classifier
([`app/vibe_model.py`](app/vibe_model.py)) is trained on the catalog's audio features (energy,
tempo, valence, danceability, acousticness) to predict a song's *vibe*
(calm / upbeat / intense / melancholy). The pipeline uses it to **re-rank** retrieved
candidates toward the vibe your request implies — so the trained model directly changes which
songs surface.

Both are wired into the main request path in [`app/pipeline.py`](app/pipeline.py):
**retrieve → re-rank (trained model) → generate (grounded) → verify**.

Example: *"sad songs for a rainy day"* → retrieves melancholy-leaning songs, the vibe model
pushes the truly melancholy ones to the top, and the reply recommends only those.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (Optional) enable Gemini generation — free key: https://aistudio.google.com/app/apikey
cp .env.example .env                 # then set GEMINI_API_KEY; skip to stay offline

python run.py                        # → http://127.0.0.1:5000
```

Open the URL, type a mood / activity / genre, and you'll get recommendations plus a
**"How this was built (RAG steps)"** panel showing retrieve → re-rank → grounding.

The vibe model trains itself on first run (a few milliseconds) and caches to
`app/models/vibe_model.joblib`. To retrain and print a cross-validated score:

```bash
python -m app.vibe_model
```

## Reliability, logging & guardrails

- **Grounding guardrail** ([`app/guardrails.py`](app/guardrails.py)): the answer may only cite
  songs that were retrieved; hallucinated titles are detected and replaced with a grounded
  response. User input is sanitized (non-empty, length-capped).
- **Logging** (`app/logs/app.log`): every request logs the query, retrieved songs, the desired
  vibe + re-ranking, grounding outcome, and timing.
- **Reproducible**: `requirements.txt`, a deterministic offline mode, a fixed model seed, and a
  network-free test suite.

## Tests

```bash
pytest                 # app/tests/
```

Covers the enriched corpus, TF-IDF retrieval relevance, the vibe model (training, prediction,
cross-validation), re-rank integration, output grounding, and the HTTP API — all deterministic.

## The data source it retrieves from

Before answering, the recommender **retrieves information from a source**: the enriched song
catalog derived from
[`module3-music-recommender/data/songs.csv`](module3-music-recommender/data/songs.csv). The
original Module 3 project is preserved in
[`module3-music-recommender/`](module3-music-recommender/) with full commit history.

## Repository layout

```
.
├── app/                        # the Music RAG Recommender
│   ├── corpus.py               # enriched song documents (RAG source)
│   ├── retriever.py            # retrieval (RAG: Retrieve) — embeddings or TF-IDF
│   ├── embeddings.py           # Gemini embeddings client (semantic search)
│   ├── vibe_model.py           # trained scikit-learn vibe classifier
│   ├── generator.py            # grounded generation (Gemini + offline)
│   ├── pipeline.py             # retrieve → re-rank → generate → verify
│   ├── guardrails.py           # input + grounding checks
│   ├── server.py               # Flask API + static UI
│   ├── static/                 # HTML · CSS · JS chat UI
│   └── tests/                  # deterministic tests
├── diagrams/architecture.mmd   # Mermaid source of truth
├── assets/architecture.png     # exported diagram
├── module3-music-recommender/  # Module 3 — base recommender + dataset (full history)
├── requirements.txt
└── run.py
```

## Architecture source

The diagram above is exported from [`diagrams/architecture.mmd`](diagrams/architecture.mmd)
(the Mermaid source of truth); the PNG in [`assets/`](assets/) is regenerated from it.
