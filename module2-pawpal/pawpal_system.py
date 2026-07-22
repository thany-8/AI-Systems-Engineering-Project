"""
pawpal_system.py
PawPal+ – Pet care scheduling system.

Classes
-------
Owner    : stores owner info and manages a list of pets
Pet      : dataclass representing a pet
Task     : dataclass representing a single care task
Schedule : organises tasks, detects conflicts, shows daily view
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


# ──────────────────────────────────────────────
# Owner
# ──────────────────────────────────────────────

class Owner:
    """Stores owner information and manages a collection of pets."""

    def __init__(self, name: str, contact: str) -> None:
        """Initialise the owner with a name and contact string."""
        self.name: str = name
        self.contact: str = contact
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Append *pet* to this owner's pet list and wire the back-reference."""
        pet.owner = self
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return self.pets

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def __str__(self) -> str:
        """Return a short string representation of the owner."""
        return f"Owner({self.name})"


# ──────────────────────────────────────────────
# Pet  (dataclass)
# ──────────────────────────────────────────────

@dataclass
class Pet:
    """Represents a pet that belongs to an owner."""

    name: str
    age: int
    species: str
    owner: Owner | None = field(default=None, repr=False)
    tasks: list[Task] = field(default_factory=list, repr=False)

    def get_info(self) -> str:
        """Return a human-readable summary of this pet."""
        owner_name = self.owner.name if self.owner else "no owner"
        task_count = len(self.tasks)
        return (
            f"{self.name} | {self.species} | age {self.age} | "
            f"owner: {owner_name} | tasks: {task_count}"
        )

    def __str__(self) -> str:
        """Return a short string representation of the pet."""
        return f"{self.name} ({self.species}, age {self.age})"


# ──────────────────────────────────────────────
# Task  (dataclass)
# ──────────────────────────────────────────────

# Lower rank = more urgent; used by Schedule.sort_tasks().
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Task:
    """Represents a single pet care task."""

    task_type: str          # e.g. "walk" | "feeding" | "medicine" | "grooming"
    pet: Pet
    date: str               # "YYYY-MM-DD"
    time: str               # "HH:MM"
    description: str = ""   # free-text detail about the activity
    frequency: str = "once" # "once" | "daily" | "weekly" | "monthly"
    duration: int = 30      # minutes — used for conflict detection
    priority: str = "medium"# "high" | "medium" | "low" — used for smart sorting
    status: str = "pending" # "pending" | "done"

    def complete(self) -> None:
        """Mark this task as done."""
        self.status = "done"

    def reschedule(self, date: str, time: str) -> None:
        """Update the task's date and time."""
        self.date = date
        self.time = time

    @property
    def priority_rank(self) -> int:
        """Numeric rank for sorting — lower means more urgent (high=0)."""
        return PRIORITY_RANK.get(self.priority.lower(), PRIORITY_RANK["medium"])

    def start_dt(self) -> datetime:
        """Return this task's start as a datetime on its own date."""
        return datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")

    def end_dt(self) -> datetime:
        """Return this task's end (start + duration) as a datetime."""
        return self.start_dt() + timedelta(minutes=self.duration)

    def occurs_on(self, target_date: str) -> bool:
        """Return True if this task falls on *target_date* given its frequency.

        Recurrence is measured from the task's own start date:
        once=only that date, daily=every day, weekly=every 7 days,
        monthly=same day-of-month. A task never occurs before its start date.
        """
        start = datetime.strptime(self.date, "%Y-%m-%d").date()
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
        if target < start:
            return False
        if self.frequency == "daily":
            return True
        if self.frequency == "weekly":
            return (target - start).days % 7 == 0
        if self.frequency == "monthly":
            return target.day == start.day
        return target == start  # "once" (and any unknown frequency)

    def __str__(self) -> str:
        """Return a formatted summary including status, priority, time, and frequency."""
        detail = f" — {self.description}" if self.description else ""
        display_time = datetime.strptime(self.time, "%H:%M").strftime("%I:%M %p").lstrip("0")
        return (
            f"[{self.status.upper()}] ({self.priority} priority) {self.task_type}{detail} "
            f"for {self.pet.name} on {self.date} at {display_time} "
            f"({self.frequency})"
        )


# ──────────────────────────────────────────────
# DailyPlan  (result of Schedule.plan_day)
# ──────────────────────────────────────────────

@dataclass
class DailyPlan:
    """A computed plan for one day: what to do, what was skipped, and why."""

    date: str
    included: list[Task]                    # tasks that fit, in the order to do them
    skipped: list[tuple[Task, str]]         # (task, reason it was left out)
    conflicts: list[tuple[Task, Task]]      # overlapping windows among included tasks
    total_minutes: int                      # minutes of included work
    available_minutes: int | None = None    # time budget, if one was given

    def explain(self) -> str:
        """Return a human-readable explanation of the plan and its reasoning."""
        lines = [f"Plan for {self.date}:"]
        if self.available_minutes is not None:
            lines.append(
                f"  Time budget: {self.available_minutes} min "
                f"| Scheduled: {self.total_minutes} min"
            )
        if self.included:
            lines.append("  Order (highest priority first, then earliest time):")
            for i, t in enumerate(self.included, start=1):
                lines.append(
                    f"    {i}. {t.time} — {t.task_type} for {t.pet.name} "
                    f"({t.priority} priority, {t.duration} min)"
                )
        else:
            lines.append("  Nothing scheduled.")
        for t, reason in self.skipped:
            lines.append(f"  Skipped {t.task_type} for {t.pet.name}: {reason}")
        for a, b in self.conflicts:
            lines.append(
                f"  ⚠ Conflict: {a.task_type} ({a.time}) overlaps "
                f"{b.task_type} ({b.time}) for {a.pet.name}"
            )
        return "\n".join(lines)


# ──────────────────────────────────────────────
# Schedule
# ──────────────────────────────────────────────

class Schedule:
    """Organises tasks by day, detects conflicts, and surfaces today's plan."""

    def __init__(self, owner: Owner) -> None:
        """Initialise the schedule for the given owner with an empty task list."""
        self.owner: Owner = owner
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the schedule and register it on the pet."""
        self.tasks.append(task)
        if task not in task.pet.tasks:
            task.pet.tasks.append(task)

    @staticmethod
    def _overlaps_on(day: str, t1: Task, t2: Task) -> bool:
        """Return True if t1 and t2 overlap in time on *day* (HH:MM windows)."""
        start1 = datetime.strptime(f"{day} {t1.time}", "%Y-%m-%d %H:%M")
        end1 = start1 + timedelta(minutes=t1.duration)
        start2 = datetime.strptime(f"{day} {t2.time}", "%Y-%m-%d %H:%M")
        end2 = start2 + timedelta(minutes=t2.duration)
        return start1 < end2 and start2 < end1

    def detect_conflicts(
        self,
        tasks: list[Task] | None = None,
        day: str | None = None,
    ) -> list[tuple[Task, Task]]:
        """Return pairs of same-pet tasks whose time windows overlap.

        With no arguments, compares every stored task against others sharing
        the same date (original behavior). When *tasks* (and optionally *day*)
        are given, all pairs are compared on that single day — used by
        plan_day so recurring tasks are checked on the day they occur.
        """
        items = self.tasks if tasks is None else tasks
        conflicts: list[tuple[Task, Task]] = []
        for i, t1 in enumerate(items):
            for t2 in items[i + 1:]:
                if t1.pet is not t2.pet:
                    continue
                if day is not None:
                    if self._overlaps_on(day, t1, t2):
                        conflicts.append((t1, t2))
                elif t1.date == t2.date and self._overlaps_on(t1.date, t1, t2):
                    conflicts.append((t1, t2))
        return conflicts

    def show_today_tasks(self) -> list[Task]:
        """Return all tasks whose date matches today."""
        return self.get_tasks_by_day(date.today().isoformat())

    def get_tasks_by_day(self, date: str) -> list[Task]:
        """Return every task that occurs on *date*, honoring recurrence.

        Uses Task.occurs_on so daily/weekly/monthly tasks surface on the
        correct days, not just their original start date.
        """
        return [t for t in self.tasks if t.occurs_on(date)]

    def get_tasks_by_pet(self, pet: Pet) -> list[Task]:
        """Return all tasks associated with a specific pet."""
        return [t for t in self.tasks if t.pet is pet]

    def get_all_owner_tasks(self) -> list[Task]:
        """Collect every task from all of the owner's pets via their back-references."""
        return [task for pet in self.owner.get_pets() for task in pet.tasks]

    def sort_tasks(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks sorted by priority (high first), then earliest start time."""
        items = self.tasks if tasks is None else tasks
        return sorted(items, key=lambda t: (t.priority_rank, t.time))

    def filter_tasks(
        self,
        tasks: list[Task] | None = None,
        *,
        status: str | None = None,
        task_type: str | None = None,
        pet: Pet | None = None,
    ) -> list[Task]:
        """Return tasks matching every provided filter (status / type / pet)."""
        items = self.tasks if tasks is None else tasks
        result: list[Task] = []
        for t in items:
            if status is not None and t.status != status:
                continue
            if task_type is not None and t.task_type != task_type:
                continue
            if pet is not None and t.pet is not pet:
                continue
            result.append(t)
        return result

    def plan_day(
        self,
        target_date: str | None = None,
        available_minutes: int | None = None,
        include_done: bool = False,
    ) -> DailyPlan:
        """Build a smart plan for *target_date* (defaults to today).

        Steps: gather the tasks that occur that day, drop completed ones
        (unless *include_done*), sort them by priority then time, then greedily
        include tasks until the optional *available_minutes* budget runs out.
        Remaining tasks are recorded as skipped with a reason.
        """
        day = target_date or date.today().isoformat()
        todays = self.get_tasks_by_day(day)
        if not include_done:
            todays = [t for t in todays if t.status != "done"]

        ordered = self.sort_tasks(todays)
        included: list[Task] = []
        skipped: list[tuple[Task, str]] = []
        used = 0
        for t in ordered:
            if available_minutes is None or used + t.duration <= available_minutes:
                included.append(t)
                used += t.duration
            else:
                remaining = max(available_minutes - used, 0)
                skipped.append(
                    (t, f"needs {t.duration} min but only {remaining} min left")
                )

        conflicts = self.detect_conflicts(included, day=day)
        return DailyPlan(
            date=day,
            included=included,
            skipped=skipped,
            conflicts=conflicts,
            total_minutes=used,
            available_minutes=available_minutes,
        )

    def __str__(self) -> str:
        """Return a short string representation of the schedule."""
        return f"Schedule({self.owner.name}, {len(self.tasks)} tasks)"
