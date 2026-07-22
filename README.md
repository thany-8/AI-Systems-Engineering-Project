# Applied AI System Project — PawPal+ Companion

An **agentic AI assistant** that helps a pet owner two ways at once: it **plans your
pets' care day** and **recommends music** to go with it. It's an evolution of my earlier
**AI-110** coursework — the two systems I built in Modules 2 and 3 are combined here
(preserved **with their full commit history** in subfolders) and exposed as **tools** that
a single LLM agent plans over, calls, and checks.

![Architecture](assets/architecture.png)

> Reasoning runs on **Google Gemini** (free tier) when a key is set, and on a
> **deterministic offline planner** otherwise — so the app always runs and is fully
> testable without an API key.

## What it does — and the advanced AI feature

The advanced feature is an **Agentic Workflow** (plan → act → check → compose), fully
integrated into the main request path in [`app/agent.py`](app/agent.py):

1. **Plan** — the planner turns a natural-language request into tool calls.
2. **Act** — the agent runs the chosen tools (the two Module engines).
3. **Check its own work** — it inspects the results and *revises*: if you asked for music
   alongside a plan, it adds a music query matched to your longest task; if a constrained
   music search matched poorly, it broadens the search.
4. **Compose** — it writes a friendly answer **grounded only in tool outputs**.

Example: *"Plan my day and pick music for it, I have 60 minutes"* → the agent builds a
prioritized care plan, notices you also want music, picks songs that suit the longest
activity, and replies with both.

## The two engines it combines

| Folder | Project | Role in the app |
|---|---|---|
| [`module2-pawpal/`](module2-pawpal/) | 🐾 **PawPal+** | `plan_pet_day`, `list_pets_and_tasks` — prioritized, conflict-aware daily plans. |
| [`module3-music-recommender/`](module3-music-recommender/) | 🎵 **Music Recommender** | `recommend_music` — content-based song scoring with reasons. |

The adapter in [`app/engines.py`](app/engines.py) imports and calls the **actual code**
from both subfolders — nothing is reimplemented.

## Quickstart

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) enable Gemini — free key: https://aistudio.google.com/app/apikey
cp .env.example .env                 # then set GEMINI_API_KEY in .env
#    Skip this step to run in offline mode.

# 4. Run
python run.py                        # → http://127.0.0.1:5000
```

Open the URL and chat. A badge shows whether you're in **Gemini** or **Offline** mode;
expand **Agent steps** under any reply to see the plan → act → check trace.

## Reliability, logging & guardrails

- **Guardrails** ([`app/guardrails.py`](app/guardrails.py)): user input is sanitized
  (non-empty, length-capped); every tool call is validated against an allow-list with
  typed, range-checked arguments; the final answer is checked for **grounding** (invented
  song titles are rejected and replaced with a grounded response).
- **Logging** (`app/logs/agent.log`): each request logs the plan, every tool call + args,
  check/revision decisions, and timing.
- **Reproducible**: `requirements.txt`, a deterministic offline mode, and a test suite
  that needs no network or API key.

## Tests

```bash
pytest                 # combined-app tests (app/tests/)
```

Covers the engines, guardrails, agent routing, the self-check/revise rules, output
grounding, and the HTTP API — all deterministic. Each original subsystem also keeps its
own tests (run from inside its folder).

## Repository layout

```
.
├── app/                        # the combined agentic app
│   ├── agent.py                # plan → act → check → compose
│   ├── llm.py                  # Gemini + deterministic offline planner
│   ├── tools.py                # tool registry (wraps both engines)
│   ├── engines.py              # imports/uses the two Module engines
│   ├── guardrails.py           # input / arg / grounding checks
│   ├── server.py               # Flask API + static UI
│   ├── static/                 # HTML · CSS · JS chat UI
│   └── tests/                  # deterministic tests
├── diagrams/architecture.mmd   # Mermaid source of truth
├── assets/architecture.png     # exported diagram
├── module2-pawpal/             # Module 2 — PawPal+ (full history)
├── module3-music-recommender/  # Module 3 — Music Recommender (full history)
├── requirements.txt
└── run.py
```

## Architecture source

The diagram above is exported from **Mermaid source** at
[`diagrams/architecture.mmd`](diagrams/architecture.mmd) (the source of truth); the PNG in
[`assets/`](assets/) is regenerated from it.
