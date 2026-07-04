# PawPal+ Project Reflection

<!-- These answers are drafted from the actual implementation. Review them and
     put them in your own voice before submitting. -->

## 1. System Design

**a. Initial design**


My Pawpal app will help an ower manage pet care task.The user can add owner information, add pet information, create care tasks, and view a daily schedule.


classes:
* Owner :
- Stores owner information like name and contact
- Can add pets.

* Pet:
- Stores pet information like name, age and species.
- Belongs to an ower

* Task:
- Stores care tasks like walk, feeding, medicine, and grooming.
- Has a date, time and status.

* Scheldule:
- Organizes tasks by day
- Detects schedule conflicts
- Shows today tasks





**b. Design changes**

Yes — the design grew during the "smart scheduling" phase. My initial `Task` only
had a type, date, time, and status. To let the app actually reason about a day, I
added three fields: `priority` (high/medium/low), `frequency`, and `duration`.

The biggest change was adding a new `DailyPlan` class. Originally `Schedule` just
returned plain lists of tasks. Once I added sorting and a time budget, a list was
no longer enough — I needed to return *what was included, what was skipped and why,
and any conflicts*. Packaging that into `DailyPlan` (with an `explain()` method)
separated "computing the plan" from "displaying the plan," which made the Streamlit
UI much simpler. I also moved recurrence into `Task.occurs_on()` so daily/weekly/
monthly tasks surface on the correct days instead of only their original date.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers four constraints: task **priority** (high/medium/low),
the **time available** today (a minutes budget), each task's **duration**, and
**time-of-day overlaps** between tasks for the same pet. Recurrence also acts as a
filter — only tasks that actually occur today are considered.

I decided **priority** mattered most: a busy owner should never drop a pet's
medicine to make room for an optional walk. The **time budget** comes second,
because time is the scarce resource that forces trade-offs. So `plan_day()` sorts by
priority first, then by earliest start time, and fills the budget in that order.

**b. Tradeoffs**

The planner is **greedy**: it sorts by priority-then-time and includes tasks until
the budget runs out. This is simple and predictable, but not globally optimal — it
won't swap one long high-priority task for two shorter ones to maximize the number
of tasks completed (a knapsack-style optimization). For a daily pet-care plan,
"most important things first" and predictable behavior matter more than squeezing in
the maximum count, so the greedy trade-off is reasonable. Relatedly, conflicts are
**surfaced, not auto-resolved** — PawPal+ flags overlaps and lets the human decide
rather than silently rescheduling something important.

---

## 3. AI Collaboration

**a. How you used AI**

I used an AI agent (GitHub Copilot CLI) for debugging, implementation, and
documentation. It caught a real bug in the demo where tasks never appeared because
`main.py` used a hardcoded date while `show_today_tasks()` filtered by the real
"today." It then implemented the smart algorithms (priority sorting, time-budget
filtering, recurrence, conflict detection, and the `DailyPlan` planner), wrote the
unit tests, wired the Streamlit UI, and generated the class diagram. The most
helpful prompts were **specific and outcome-oriented** ("make the app smart:
sorting, filtering, recurring tasks, conflict detection") and answering its design
questions **one at a time** (e.g., picking a priority scheme).

**b. Judgment and verification**

I didn't accept everything as-is. When adding priority, the agent offered a numeric
1–5 scheme, but I chose **High/Medium/Low** because it reads more clearly in the UI
and maps cleanly to three sort ranks. I verified every change rather than trusting
it: running `pytest` (10 tests), running `python main.py` to read an actual plan,
and booting the Streamlit app to confirm it served with no errors. I also asked for
**small, atomic commits** so each change was easy to review on its own.

---

## 4. Testing and Verification

**a. What you tested**

I tested the behaviors that make the scheduler "smart":
- **Priority sorting** — high before medium before low, with ties broken by time.
- **Time-budget filtering** — a low-priority task is skipped when it doesn't fit.
- **Recurrence** — `occurs_on()` for once / daily / weekly / monthly.
- **Conflict detection** — overlapping vs. non-overlapping same-pet tasks.
- Plus the original tests for marking a task done and task counts.

These matter because they are the core guarantees a user relies on: the right tasks,
in the right order, within the time they actually have.

**b. Confidence**

Fairly confident — 10 passing unit tests cover the core logic, and both the CLI demo
and the Streamlit UI exercise it end to end without errors. Edge cases I'd test next:
monthly recurrence on the 31st (short months), tasks that cross midnight, several
pets with interleaved conflicts, and performance with a very large task list.

---

## 5. Reflection

**a. What went well**

Keeping the **logic (`pawpal_system.py`) separate from the UI (`app.py`)** paid off:
I could add each smart feature and test it in isolation without touching Streamlit.
The part I'm most satisfied with is `DailyPlan.explain()` — the app doesn't just
produce a plan, it explains *why* it chose that order and what it skipped.

**b. What you would improve**

Next iteration I'd add **task editing and deleting** in the UI, **persist data**
(right now everything lives in the Streamlit session), suggest a new time when a
**conflict** is detected instead of just flagging it, and replace the greedy planner
with a real optimizer. I'd also refine monthly recurrence to handle month-end.

**c. Key takeaway**

Designing the **data model and small algorithms first**, then letting the UI simply
render them, kept the system understandable and testable. And working with an AI
agent is most effective when you give it **specific goals, make the design decisions
yourself, and verify every change** with tests and a real run — not when you treat
its output as automatically correct.
