# 🎬 Demo Script — AI Playlist Generator, Personalized and Explainable

A ~6–7 minute walkthrough you can record over, written in the same first-person, conversational
voice as your Loom. Each beat has **► Show** (what to do on screen) and **🎙 Say** (the narration).
Run the app first: `python run.py` → http://127.0.0.1:5050

> Tip: keep a browser tab on the landing page, and have the README + the Excalidraw diagram
> (`assets/architecture.png`) open in a second tab for the "under the hood" section.

---

## 0:00 — Intro (~30s)
**► Show:** the landing page — the hero "Create the perfect playlist in seconds".

🎙 "Hi — this is my **AI Playlist Generator**. You describe the music you want in plain language —
a mood, an activity, a genre — and it builds you a ranked, *explained* playlist. It started as my
Module 3 **Music Recommender**, which just scored a fixed song catalog by its audio features. I grew
it into a full web app with retrieval-augmented generation, a trained ranking model, accounts, and
personalization — and the whole thing still runs offline, with no API key required."

---

## 0:30 — First playlist (~45s)
**► Show:** type *"sad songs for a rainy day"* → **Create Playlist**. Let the skeleton loader run,
then the card appears.

🎙 "Let's try one. I'll ask for *sad songs for a rainy day*. While it works you can see a loading
state — it's actually running a full pipeline behind the scenes. And here's the playlist: each track
shows the artist, genre and mood tags, and a **match score**. Up top it detected the **melancholy**
vibe on its own. Every song also has **Play on Spotify, YouTube, or Apple Music** links, so I can
jump straight to it."

---

## 1:15 — Intensity, and how it actually changes results (~50s)
**► Show:** type *"music for studying"* → Create. Then click the **Intensity → High** button, then
**Low**, so the song list visibly changes.

🎙 "One thing I really wanted was *nuance* — like intensity. Watch this: same request, *music for
studying*. If I set intensity to **High**, I get energetic tracks like Blinding Lights and Gym Hero.
Switch to **Low**, and it swaps to calm, low-energy songs — lofi, ambient, that kind of thing. This
was actually one of my hardest problems: at first intensity only *re-ordered* the same songs, so it
looked like it did nothing. I fixed it so intensity also **biases retrieval** — it changes *which*
songs get pulled in, not just their order."

---

## 2:05 — Sign up (Camille) & accounts (~40s)
**► Show:** click **Sign up** → create the account (e.g. Camille) → land back on the home page,
logged in (the user chip shows in the corner).

🎙 "Now let me make an account — I'll sign up as **Camille**. Accounts are email and password;
passwords are stored only as a salted hash, never in plain text. Everything's saved in a local
SQLite database, and each account is **private** — you only ever see your own playlists. Notice the
'Simple, free to start' panel disappears once I'm signed in, since I already have an account."

---

## 2:45 — Reactions + personalization with explanations (~55s)
**► Show:** on a generated playlist, click 👍 on a couple of tracks (e.g. an upbeat one) and 👎 on one.
Then regenerate a related query (e.g. *"feel good songs"*) so the **✨ Personalized from your history**
line and the green per-track "why" chips appear.

🎙 "Here's the part I'm most proud of — it **learns from me**. I can thumbs-up songs I like and
thumbs-down ones I don't. Now when I generate again, look — it says **'Personalized from your
history — 2 reactions and 1 saved playlist'**, and each track it boosted tells me *why*: things like
**'✨ you like Voltline'** or **'matches your upbeat taste.'** It learns from both my reactions *and*
the playlists I save, and it's a bounded nudge — it personalizes the order without ever drowning out
relevance. And a small detail I fixed: the match score is always a clean **0 to 100%** now."

---

## 3:40 — Save + library + quick moods (~40s)
**► Show:** click **＋ Save playlist** → open **My playlists** (the library) → show the saved card and
the taste-profile summary. Then back on home, open **Quick actions** and pick a mood (rainy / gym /
Latin party) to show it fills and generates in place.

🎙 "I'll save this to my library. On the library page I can see everything I've saved, plus a little
**taste profile** — the vibes, genres, and artists it's learned I like. And for speed, **Quick
actions** gives me one-click moods — rainy day, gym, Latin party — which generate right in place
without reloading."

---

## 4:20 — Under the hood: the four-stage pipeline (~55s)
**► Show:** open the README's **Excalidraw architecture diagram** (`assets/architecture.png`).

🎙 "So how does it work? It's a four-stage **RAG pipeline**. **One — Retrieve:** every song is turned
into a text description, and I match the request against them, using Gemini embeddings if a key's
set, or local TF-IDF otherwise. **Two — Re-rank:** a trained **logistic-regression** model predicts a
song's vibe from features like energy, tempo, and valence, and I blend that with the retrieval score
— plus intensity and personalization. **Three — Generate:** it writes the explanation with **Gemini**,
or a deterministic **offline template** when there's no key. **Four — Verify:** a grounding guardrail
checks the answer only cites songs that were actually retrieved — if it ever hallucinates a title, I
throw the answer out and fall back to a safe offline one."

---

## 5:15 — Reliability & engineering (~50s)
**► Show:** (optional) a terminal running `pytest` showing 48 passing, or just talk over the app.

🎙 "I put a lot into making this *reliable*, not just clever. The whole system runs **offline and
deterministically**, so it never depends on an external AI service to work — which also means I can
test it. There are **48 automated tests** covering retrieval, the model, grounding, the API, accounts,
and personalization. It's **hardened** too: the endpoints are **rate-limited**, the free-text input is
screened for **prompt injection** — and if it looks like an attack, it skips the LLM entirely. And
running it under a real production server surfaced great bugs, like two workers racing to create the
database — all fixed. It ships with a **Docker + gunicorn** setup for deployment."

---

## 6:05 — Honest limits & what's next (~40s)
**► Show:** back on the app, or the model card (`module3-music-recommender/model_card.md`).

🎙 "I want to be honest about the limits. The catalog is only **30 songs, manually labeled**, so lots
of genres, languages, and cultures are missing, and the model collapses moods into four broad vibes,
so nuance gets lost. Next, I'd **expand the dataset** a lot, add richer signals like skips and repeat
plays, and evaluate genre coverage and fairness more systematically. The full responsible-AI write-up
is in my model card."

---

## 6:45 — Close (~15s)
**► Show:** the landing page.

🎙 "So that's the AI Playlist Generator — personalized, explainable, grounded, and reliable, from a
plain-language request all the way to a saved playlist. Thanks for watching!"

---

### 🎯 Quick shot list (if you want to record in one take)
1. Landing page → generate "sad songs for a rainy day"
2. "music for studying" → toggle Intensity High ↔ Low
3. Sign up as Camille
4. 👍 / 👎 a few tracks → regenerate → show the "Personalized" line + why-chips
5. Save playlist → open library (taste profile) → Quick actions mood
6. Excalidraw diagram → explain the 4 stages
7. (optional) `pytest` = 48 passing → mention rate-limiting / injection defense / Docker
8. Model card → limits & future → close
