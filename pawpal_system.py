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
        return f"{self.name} ({self.species}, age {self.age})"


# ──────────────────────────────────────────────
# Task  (dataclass)
# ──────────────────────────────────────────────

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
    status: str = "pending" # "pending" | "done"

    def complete(self) -> None:
        """Mark this task as done."""
        self.status = "done"

    def reschedule(self, date: str, time: str) -> None:
        """Update the task's date and time."""
        self.date = date
        self.time = time

    def __str__(self) -> str:
        detail = f" — {self.description}" if self.description else ""
        display_time = datetime.strptime(self.time, "%H:%M").strftime("%I:%M %p").lstrip("0")
        return (
            f"[{self.status.upper()}] {self.task_type}{detail} "
            f"for {self.pet.name} on {self.date} at {display_time} "
            f"({self.frequency})"
        )


# ──────────────────────────────────────────────
# Schedule
# ──────────────────────────────────────────────

class Schedule:
    """Organises tasks by day, detects conflicts, and surfaces today's plan."""

    def __init__(self, owner: Owner) -> None:
        self.owner: Owner = owner
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the schedule and register it on the pet."""
        self.tasks.append(task)
        if task not in task.pet.tasks:
            task.pet.tasks.append(task)

    def detect_conflicts(self) -> list[tuple[Task, Task]]:
        """Return pairs of tasks for the same pet whose time windows overlap."""
        conflicts: list[tuple[Task, Task]] = []
        for i, t1 in enumerate(self.tasks):
            for t2 in self.tasks[i + 1:]:
                if t1.pet is not t2.pet or t1.date != t2.date:
                    continue
                start1 = datetime.strptime(f"{t1.date} {t1.time}", "%Y-%m-%d %H:%M")
                end1 = start1 + timedelta(minutes=t1.duration)
                start2 = datetime.strptime(f"{t2.date} {t2.time}", "%Y-%m-%d %H:%M")
                end2 = start2 + timedelta(minutes=t2.duration)
                if start1 < end2 and start2 < end1:
                    conflicts.append((t1, t2))
        return conflicts

    def show_today_tasks(self) -> list[Task]:
        """Return all tasks whose date matches today."""
        return self.get_tasks_by_day(date.today().isoformat())

    def get_tasks_by_day(self, date: str) -> list[Task]:
        """Return all tasks scheduled for *date* (format 'YYYY-MM-DD')."""
        return [t for t in self.tasks if t.date == date]

    def get_tasks_by_pet(self, pet: Pet) -> list[Task]:
        """Return all tasks associated with a specific pet."""
        return [t for t in self.tasks if t.pet is pet]

    def get_all_owner_tasks(self) -> list[Task]:
        """Collect every task from all of the owner's pets via their back-references."""
        return [task for pet in self.owner.get_pets() for task in pet.tasks]

    def __str__(self) -> str:
        return f"Schedule({self.owner.name}, {len(self.tasks)} tasks)"
