# Music RAG Recommender

Describe a mood, activity, or genre in plain language and this app recommends songs and explains
why. It **retrieves** matching songs from a local catalog (**RAG**), **re-ranks** them with a
**trained scikit-learn "vibe" model**, and **generates** a grounded explanation — using **Google
Gemini** (free tier) when a key is set, or a fully local **offline** mode otherwise.

## Architecture overview

![Architecture](assets/architecture.png)

A **Flask** app serves an HTML chat UI and runs a four-stage **RAG pipeline**: **retrieve**
relevant songs (semantic Gemini embeddings, or local TF-IDF), **re-rank** them with the trained
vibe classifier, **generate** a grounded answer (Gemini or an offline template), and **verify**
it. A component + testing view is in
[`diagrams/system-overview.mmd`](diagrams/system-overview.mmd).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # optional: add a free GEMINI_API_KEY; skip to run offline
python run.py                        # → http://127.0.0.1:5000
```

## Sample interaction

> **You:** sad songs for a rainy day
>
> **Recommender:**
> - "Someone Like You" by Adele — sad pop, melancholy vibe (match 0.97)
> - "Lovely" by Billie Eilish and Khalid — sad alternative-pop, melancholy vibe (match 0.89)
> - "Shallow" by Lady Gaga and Bradley Cooper — emotional pop, melancholy vibe (match 0.70)
>
> *RAG steps: retrieve → re-rank (desired vibe: melancholy) → grounding passed*

## Design decisions

- **RAG over an enriched catalog** — structured songs become descriptive text so retrieval matches
  by meaning, and the model answers **only** from retrieved songs.
- **Trained vibe model for re-ranking** — a lightweight scikit-learn classifier (not a heavy
  fine-tune) is fast, free, and genuinely shapes which songs surface.
- **Gemini free tier + offline fallback** — real embeddings and generation with a key, but the app
  always runs and stays testable without one.
- **Grounding guardrail** — invented song titles are detected and replaced, keeping answers
  faithful to the data.

## Testing

`pytest` runs deterministically offline and covers retrieval relevance, the vibe model (training,
prediction, cross-validation ≈ 0.70), the embedding retriever, re-rank integration, output
grounding, and the HTTP API. At runtime, the grounding guardrail additionally checks every
generated answer for hallucinated songs before it reaches the user.

## Reflection

This project taught me a lot about **applied AI and problem-solving** — how to combine retrieval, a
trained model, and generation into one reliable pipeline, and how to keep AI outputs grounded and
testable instead of trusting them blindly. It also taught me how to **collaborate with AI**:
breaking an open-ended goal into clear decisions, iterating through pivots, and verifying results
at each step.
