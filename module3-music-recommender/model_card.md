# Model Card: AI Playlist Generator

## 1. Model Name

**AI Playlist Generator (VibeFlow RAG Playlist Recommender)**

This project started as a small content-based music recommender and evolved into a Flask web app that generates grounded playlist suggestions from a local song catalog. The current system combines retrieval, a trained scikit-learn vibe model, optional Gemini generation, account-based playlist saving, personalization from user feedback, and reliability hardening (rate limiting, prompt-injection screening, and a Docker / gunicorn deployment path).

---

## 2. Intended Use

The system is designed for learners and casual music listeners who want playlist suggestions based on a mood, activity, or genre described in natural language, such as:

- calm music for studying
- sad songs for a rainy day
- upbeat songs for the gym

The app is intended for classroom exploration of applied AI, retrieval-augmented generation, lightweight model training, and reliability guardrails. It is not a production music platform and should not be treated as a replacement for Spotify, Apple Music, YouTube Music, or other large-scale recommender systems.

The intended outputs are:

- a ranked list of songs from the local catalog
- a short explanation of why those songs fit the query
- a saved playlist for a logged-in user if they choose to store it

---

## 3. System Overview

The current app is no longer a simple one-step content scorer. It now uses a four-stage pipeline:

1. **Retrieve** relevant songs from the local catalog.
2. **Re-rank** the retrieved songs using a trained vibe classifier.
3. **Generate** a grounded response from the ranked results.
4. **Verify** that the answer cites only songs that were actually retrieved.

The system runs as a Flask web application with:

- a landing page for playlist generation
- signup and login pages
- a personal library page for saved playlists
- a local SQLite database for user accounts, saved playlists, and reactions
- 👍 / 👎 reactions and a per-user taste profile that personalizes future rankings
- an intensity control (Low / Medium / High) and per-song "why it was picked" explanations

This means the project now combines classic software engineering with AI pipeline design rather than only demonstrating recommendation logic in isolation.

---

## 4. How the AI Works

### Retrieval

Each song in the dataset is converted into a natural-language description that includes genre, mood, energy, tempo, valence, danceability, acousticness, and likely listening contexts such as studying, relaxing, or working out.

The retriever then matches the user query against those song descriptions using one of two modes:

- **TF-IDF retrieval** for deterministic, fully local offline behavior
- **Gemini embeddings** for semantic retrieval when an API key is available

If Gemini embeddings are unavailable or fail, the app falls back to TF-IDF so the system still works.

### Re-ranking with a Trained Model

After retrieval, the app uses a trained logistic regression classifier to predict one of four broad vibes for each candidate song:

- calm
- upbeat
- intense
- melancholy

The model uses numerical song features:

- energy
- tempo
- valence
- danceability
- acousticness

The final ranking blends retrieval relevance (`0.6`) with the vibe-model match (`0.4`). When the user
requests an **intensity** (e.g. "high-energy", or the Low / Medium / High control), a target song
energy is folded in and also biases retrieval; and for a signed-in user, a **taste profile** built
from their 👍 / 👎 reactions and saved playlists applies a small, bounded, per-song nudge (each
explained in the UI). Both are additive layers, so the default blend is unchanged when there is no
requested intensity or user history.

### Generation

The app then generates a recommendation summary using:

- **Gemini** when a key is configured, or
- a **deterministic offline template** when no key is available

In both modes, the response is constrained to the retrieved songs.

### Guardrails

The app includes two main guardrails:

- **Input validation** rejects empty or excessively long queries.
- **Grounding verification** checks whether the generated response mentions any quoted song titles that were not retrieved. If hallucinated titles are detected, the app replaces the answer with a safe offline response built only from known songs.

---

## 5. Data

The current catalog contains **30 songs** stored in a CSV file inherited from the earlier Module 3 recommender.

Each song includes:

- title
- artist
- genre
- mood
- energy
- tempo in BPM
- valence
- danceability
- acousticness

The catalog includes genres such as pop, reggaeton, salsa, lofi, jazz, funk, afrobeats, synthwave, rock-related styles, and several pop subgenres. It also includes moods such as happy, sad, relaxed, energetic, intense, focused, playful, romantic, dark, and emotional.

This dataset is still small and manually curated. It remains useful for demonstrating recommendation, retrieval, ranking, and grounding behavior, but it is not large or diverse enough to support broad real-world personalization claims.

---

## 6. Strengths

The current system has several important strengths compared with the earlier prototype:

- It accepts natural-language requests instead of requiring a fixed profile object.
- It supports both offline operation and optional Gemini-powered semantic retrieval/generation.
- It includes a trained specialized model that directly changes ranking behavior.
- It provides explanations instead of only returning scores.
- It uses a grounding guardrail to reduce hallucinated song recommendations.
- It stores playlists per user account, which makes the app feel like a complete product rather than only a script.
- It exposes a trace of pipeline steps, which improves transparency during testing and debugging.
- It personalizes rankings from a user's own history (reactions + saved playlists) and explains each bias per song.
- It is hardened for real use: per-client rate limiting, prompt-injection screening, and a Docker / gunicorn deployment path.

Another strength is reliability under constrained conditions. The system is designed so that it still works without network access or an API key, which made development and automated testing more stable.

---

## 7. Limitations or Biases in the System

This system still has several limitations and potential biases:

- The song catalog is small, so many genres, languages, cultures, and listening contexts are missing or underrepresented.
- Song features and moods are manually labeled, which introduces human subjectivity.
- The vibe model collapses many moods into only four broad classes, so nuance is lost.
- Retrieval depends on synthetic text descriptions written from structured metadata, not from full audio or lyrics.
- The app may favor songs whose metadata happens to align well with the wording used in the query or corpus descriptions.
- The ranking blend gives substantial influence to retrieval relevance and the vibe model, so songs outside those patterns may be ignored even if a listener would enjoy them.
- The system learns from explicit reactions (👍 / 👎) and saved playlists, but not from implicit
  signals such as skips, repeated plays, listening duration, or long-term cross-session behavior.
- The app does not analyze lyrics, language, artist background, release year, or broader cultural context.
- Because the same curated dataset is used throughout the system, any bias in the catalog is amplified by retrieval, ranking, and generation.
- A grounded answer can still be limited or repetitive even when it is factually faithful to the retrieved songs.

In short, the system is better at being consistent and explainable than at being globally representative or deeply personalized.

---

## 8. Could the AI Be Misused, and How Would We Prevent That?

Yes. The system could be misused in smaller but still important ways.

Possible misuse includes:

- presenting the recommendations as if they were comprehensive or professionally validated
- over-trusting generated explanations even when the catalog is narrow
- trying to treat the app like an open-ended music assistant when it only knows the local dataset
- probing account or playlist endpoints without authentication

Current prevention measures include:

- **Grounding guardrails** so generated answers only cite retrieved songs from the local catalog
- **Input validation** to reject invalid or oversized requests
- **Authentication requirements** for accessing and saving playlists
- **Password hashing** so user passwords are not stored in plain text
- **Per-user playlist isolation** so users cannot access or delete each other's saved playlists
- **Offline fallback behavior** so the app does not fail open if an external model is unavailable
- **Rate limiting** on the recommendation and auth endpoints (per client) to curb abuse and brute-force attempts
- **Prompt-injection screening** that sanitizes the free-text query and, on a suspected attempt, bypasses the LLM for the deterministic offline generator

Additional future protections could include:

- stronger monitoring and account lockout for repeated failed login attempts
- more explicit UI warnings that the app is educational and catalog-limited
- content moderation rules if the prompt surface is expanded beyond music recommendation

---

## 9. Evaluation and Reliability Testing

The project now includes an automated `pytest` suite that runs offline and checks much more than the original prototype.

The tests cover:

- corpus creation from the CSV catalog
- retrieval relevance for calm and sad queries
- TF-IDF fallback behavior when Gemini is unavailable
- embedding retriever ranking behavior
- vibe-model training, prediction, probability output, and cross-validation reporting
- vibe detection from natural-language queries
- full pipeline behavior from retrieval through grounding
- guardrail handling when a generator hallucinates a fake song title
- HTTP API behavior for healthy and invalid requests
- signup, login, logout, and duplicate-account handling
- password hashing
- authenticated playlist saving and deletion
- per-user playlist isolation
- intensity detection and its effect on ranking
- taste-profile personalization from reactions and saved playlists, with per-song explanations
- input sanitization, prompt-injection detection that bypasses the LLM, and rate-limit responses

At the time of the latest test run, the suite reported **47 passing tests**.

One internal evaluation signal from the trained vibe model is cross-validated accuracy on the 30-song dataset. That metric is useful for checking whether the model learns something meaningful, but it should be interpreted cautiously because the dataset is small.

---

## 10. What Surprised Me While Testing Reliability?

One of the most surprising results was that the reliability work mattered as much as the recommendation logic itself.

In particular, it was surprising that a generator could produce a convincing but fake song title so easily, while the grounding guardrail could still catch that error and force a safer offline answer. That showed me that a fluent response is not automatically a trustworthy one.

Another surprising result was how well the app could remain usable without external AI services. Even when Gemini is unavailable, the offline retriever and template generator still let the full system run and pass tests deterministically. That made the app more reliable than I initially expected.

It was also interesting that a relatively simple logistic regression vibe model could still influence ranking in a noticeable way, even though the dataset is small and the overall architecture is much simpler than a commercial recommendation system.

---

## 11. Collaboration With AI During the Project

AI was used as a development partner for brainstorming, structuring code, refining prompts, and checking edge cases, but not as a source of truth that could be accepted without review.

One helpful AI suggestion was to separate the recommendation flow into clear stages: retrieval, re-ranking, generation, and verification. That suggestion improved the system architecture because each step became easier to test, debug, and explain. It also directly supported features that now exist in the codebase, such as the pipeline trace and the grounding guardrail fallback.

One flawed AI suggestion was the tendency to assume that a generated recommendation would be reliable if the prompt simply told the model not to invent songs. In practice, prompt instructions alone were not enough. That idea was incomplete, because the system still needed explicit verification logic to detect hallucinated song titles and replace unsafe output. This was a useful reminder that AI suggestions can be directionally helpful while still being technically insufficient.

Overall, the collaboration worked best when AI was used to accelerate implementation ideas and surface options, while final design choices were validated through tests and manual review.

---

## 12. Future Work

Future versions of the system could improve by:

- expanding the catalog far beyond 30 songs
- adding more genres, languages, and international music
- extending feedback signals beyond 👍 / 👎 and saved playlists to skips and repeat plays
- improving diversity so recommendations are not too similar to one another
- further security hardening such as account lockout and CSRF protection
- improving explainability with per-feature score breakdowns
- evaluating fairness and genre coverage more systematically
- adding richer metadata such as lyrics, release year, and language
- combining content-based signals with collaborative filtering or sequence models

---

## 13. Reflection

This project changed from a straightforward content-based recommender into a more complete AI application. The most important lesson was that building an AI feature is not only about getting an answer; it is about making the answer reproducible, bounded by data, testable, and safe enough for the intended use.

The project also showed that even a small educational app can benefit from core AI engineering ideas: fallback modes, transparent pipeline stages, automated tests, authentication boundaries, and explicit guardrails against hallucination.