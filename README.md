# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
# Launch the Streamlit UI (opens at http://localhost:8501):
streamlit run app.py

# …or run the command-line demo:
python main.py
```

In the UI you save an owner, add pets, add care tasks (type, date/time, duration,
priority, and how often they repeat), then enter how many minutes you have today
to get a prioritized daily plan.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
====================================================
  PawPal+ — Today's Schedule (2026-07-03)
  Owner : Alice  |  alice@example.com
  Pets  : Max (dog, age 4), Luna (cat, age 2)
====================================================
  [PENDING] (high priority) medicine — Flea treatment drops for Luna on 2026-07-03 at 9:30 AM (monthly)
  [PENDING] (high priority) grooming — Quick brush-down for Max on 2026-07-03 at 12:05 PM (weekly)
  [PENDING] (medium priority) feeding — Dry kibble — one cup for Max on 2026-07-03 at 12:00 PM (daily)
  [PENDING] (low priority) walk — Morning walk around the park for Max on 2026-07-03 at 8:00 AM (daily)

----------------------------------------------------
  Smart plan for a 40-minute window
----------------------------------------------------
Plan for 2026-07-03:
  Time budget: 40 min | Scheduled: 35 min
  Order (highest priority first, then earliest time):
    1. 09:30 — medicine for Luna (high priority, 5 min)
    2. 12:05 — grooming for Max (high priority, 20 min)
    3. 12:00 — feeding for Max (medium priority, 10 min)
  Skipped walk for Max: needs 30 min but only 5 min left
  ⚠ Conflict: grooming (12:05) overlaps feeding (12:00) for Max
====================================================
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```

======================= test session starts =======================
platform darwin -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/thany/Documents/Development/AI_Engeneer Project #2
plugins: anyio-4.14.1
collected 10 items                                                

tests/test_pawpal.py ..........                             [100%]

======================== 10 passed in 0.01s =======================
```

## 📐 Smarter Scheduling

PawPal+ turns a raw task list into an ordered daily plan using a few simple algorithms:

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Schedule.sort_tasks` | Sorts by priority (high → low), then earliest start time. |
| Filtering | `Schedule.filter_tasks`, `Schedule.plan_day` | `filter_tasks` narrows by status/type/pet; `plan_day` greedily fits tasks into an available-minutes budget and skips the rest. |
| Conflict handling | `Schedule.detect_conflicts` | Flags overlapping time windows for the same pet (start/duration overlap). |
| Recurring tasks | `Task.occurs_on`, `Schedule.get_tasks_by_day` | `once` / `daily` / `weekly` (every 7 days) / `monthly` (same day-of-month), measured from the task's start date. |
| Plan reasoning | `Schedule.plan_day` → `DailyPlan.explain` | Returns the chosen order, skipped tasks (with reasons), conflicts, and total scheduled minutes. |

## 📸 Demo Walkthrough

Follow these steps to reproduce a full plan in the Streamlit UI:

1. **Save the owner** — enter a name and contact, then click **Save owner**. This creates the `Owner` and an empty `Schedule` for the session.
2. **Add a pet** — enter a name, age, and species and click **Add pet**. Repeat to add more pets (e.g., Max the dog and Luna the cat).
3. **Add care tasks** — for each task pick the pet, type (walk/feeding/medicine/grooming), date, time, description, **frequency** (once/daily/weekly/monthly), **duration**, and **priority** (high/medium/low), then click **Add task**.
4. **Set your time budget** — under *Smart Daily Plan*, enter how many minutes you have today (`0` = no limit).
5. **Read the plan** — PawPal+ lists today's tasks **highest priority first, then earliest time**, marks any that **don't fit the time budget** as skipped (with the reason), flags **time conflicts** for the same pet, and offers a **"Why this plan?"** explanation. Click **Done** to complete a task and watch the plan update.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
