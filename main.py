"""
main.py
PawPal+ – demo script.

Creates an Owner, two Pets, three Tasks, and prints Today's Schedule.
"""
from pawpal_system import Owner, Pet, Task, Schedule


TODAY = "2026-06-30"


def main() -> None:
    # ── 1. Owner ──────────────────────────────
    owner = Owner("Alice", "alice@example.com")

    # ── 2. Two Pets ───────────────────────────
    max_ = Pet(name="Max", age=4, species="dog")
    luna = Pet(name="Luna", age=2, species="cat")
    owner.add_pet(max_)
    owner.add_pet(luna)

    # ── 3. Three Tasks with different times ───
    schedule = Schedule(owner)

    t1 = Task(
        task_type="walk",
        pet=max_,
        date=TODAY,
        time="08:00",
        description="Morning walk around the park",
        frequency="daily",
        duration=30,
    )
    t2 = Task(
        task_type="feeding",
        pet=max_,
        date=TODAY,
        time="12:00",
        description="Dry kibble — one cup",
        frequency="daily",
        duration=10,
    )
    t3 = Task(
        task_type="medicine",
        pet=luna,
        date=TODAY,
        time="09:30",
        description="Flea treatment drops",
        frequency="monthly",
        duration=5,
    )

    schedule.add_task(t1)
    schedule.add_task(t2)
    schedule.add_task(t3)

    # ── 4. Print Today's Schedule ─────────────
    print(f"\n{'=' * 40}")
    print(f"  PawPal+ — Today's Schedule ({TODAY})")
    print(f"  Owner : {owner.name}  |  {owner.contact}")
    print(f"  Pets  : {', '.join(str(p) for p in owner.get_pets())}")
    print(f"{'=' * 40}")

    today_tasks = schedule.show_today_tasks()
    if today_tasks:
        for task in today_tasks:
            print(f"  {task}")
    else:
        print("  No tasks scheduled for today.")

    conflicts = schedule.detect_conflicts()
    if conflicts:
        print(f"\n  ⚠ Conflicts detected:")
        for a, b in conflicts:
            print(f"    • {a.task_type} ({a.time}) overlaps with {b.task_type} ({b.time}) for {a.pet.name}")

    print(f"{'=' * 40}\n")


if __name__ == "__main__":
    main()

