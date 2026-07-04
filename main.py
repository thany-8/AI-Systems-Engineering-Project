"""
main.py
PawPal+ – demo script.

Creates an Owner, two Pets, three Tasks, and prints Today's Schedule.
"""
from datetime import date

from pawpal_system import Owner, Pet, Task, Schedule


# Use the real current date so the tasks created below land on "today" and
# Schedule.show_today_tasks() (which filters by date.today()) actually shows them.
TODAY = date.today().isoformat()


def main() -> None:
    # ── 1. Owner ──────────────────────────────
    owner = Owner("Alice", "alice@example.com")

    # ── 2. Two Pets ───────────────────────────
    max_ = Pet(name="Max", age=4, species="dog")
    luna = Pet(name="Luna", age=2, species="cat")
    owner.add_pet(max_)
    owner.add_pet(luna)

    # ── 3. Tasks with priorities, durations, and recurrence ───
    schedule = Schedule(owner)

    schedule.add_task(Task(
        task_type="walk", pet=max_, date=TODAY, time="08:00",
        description="Morning walk around the park",
        frequency="daily", duration=30, priority="low",
    ))
    schedule.add_task(Task(
        task_type="feeding", pet=max_, date=TODAY, time="12:00",
        description="Dry kibble — one cup",
        frequency="daily", duration=10, priority="medium",
    ))
    schedule.add_task(Task(
        task_type="grooming", pet=max_, date=TODAY, time="12:05",
        description="Quick brush-down",
        frequency="weekly", duration=20, priority="high",
    ))
    schedule.add_task(Task(
        task_type="medicine", pet=luna, date=TODAY, time="09:30",
        description="Flea treatment drops",
        frequency="monthly", duration=5, priority="high",
    ))

    # ── 4. Header + today's tasks (sorted by priority, then time) ───
    print(f"\n{'=' * 52}")
    print(f"  PawPal+ — Today's Schedule ({TODAY})")
    print(f"  Owner : {owner.name}  |  {owner.contact}")
    print(f"  Pets  : {', '.join(str(p) for p in owner.get_pets())}")
    print(f"{'=' * 52}")

    today_tasks = schedule.sort_tasks(schedule.show_today_tasks())
    if today_tasks:
        for task in today_tasks:
            print(f"  {task}")
    else:
        print("  No tasks scheduled for today.")

    # ── 5. Smart plan within a limited time budget ───
    available_minutes = 40
    print(f"\n{'-' * 52}")
    print(f"  Smart plan for a {available_minutes}-minute window")
    print(f"{'-' * 52}")
    plan = schedule.plan_day(available_minutes=available_minutes)
    print(plan.explain())

    print(f"{'=' * 52}\n")


if __name__ == "__main__":
    main()

