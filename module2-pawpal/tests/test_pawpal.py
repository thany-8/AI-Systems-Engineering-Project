import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Owner, Pet, Task, Schedule


class TestTaskCompletion(unittest.TestCase):
    """Verify that complete() changes a task's status to 'done'."""

    def test_mark_complete_changes_status(self):
        pet = Pet(name="Max", age=3, species="dog")
        task = Task(task_type="walk", pet=pet, date="2026-07-01", time="09:00")

        self.assertEqual(task.status, "pending")   # starts pending
        task.complete()
        self.assertEqual(task.status, "done")       # now done


class TestTaskAddition(unittest.TestCase):
    """Verify that adding a task to a Pet increases its task count."""

    def test_adding_task_increases_pet_task_count(self):
        owner = Owner("Alice", "alice@example.com")
        pet = Pet(name="Max", age=3, species="dog")
        owner.add_pet(pet)
        schedule = Schedule(owner)

        self.assertEqual(len(pet.tasks), 0)         # no tasks yet

        task = Task(task_type="feeding", pet=pet, date="2026-07-01", time="08:00")
        schedule.add_task(task)

        self.assertEqual(len(pet.tasks), 1)         # task count increased


class TestPrioritySorting(unittest.TestCase):
    """Verify sort_tasks orders by priority (high first), then time."""

    def test_sorts_by_priority_then_time(self):
        owner = Owner("Alice", "alice@example.com")
        pet = Pet(name="Max", age=3, species="dog")
        owner.add_pet(pet)
        schedule = Schedule(owner)

        low = Task(task_type="walk", pet=pet, date="2026-07-03", time="08:00", priority="low")
        high = Task(task_type="medicine", pet=pet, date="2026-07-03", time="09:30", priority="high")
        med_early = Task(task_type="feeding", pet=pet, date="2026-07-03", time="07:00", priority="medium")
        med_late = Task(task_type="grooming", pet=pet, date="2026-07-03", time="18:00", priority="medium")
        for t in (low, high, med_early, med_late):
            schedule.add_task(t)

        ordered = schedule.sort_tasks()

        # high first, then the two mediums by time (07:00 before 18:00), low last
        self.assertEqual(ordered, [high, med_early, med_late, low])


class TestTimeBudgetFiltering(unittest.TestCase):
    """Verify plan_day skips tasks once the time budget runs out."""

    def test_skips_tasks_when_time_runs_out(self):
        owner = Owner("Alice", "alice@example.com")
        pet = Pet(name="Max", age=3, species="dog")
        owner.add_pet(pet)
        schedule = Schedule(owner)

        high = Task(task_type="medicine", pet=pet, date="2026-07-03", time="09:00",
                    duration=20, priority="high")
        low = Task(task_type="walk", pet=pet, date="2026-07-03", time="10:00",
                   duration=30, priority="low")
        schedule.add_task(high)
        schedule.add_task(low)

        plan = schedule.plan_day("2026-07-03", available_minutes=25)

        self.assertEqual(plan.included, [high])          # high priority fits (20 <= 25)
        self.assertEqual(plan.total_minutes, 20)
        self.assertEqual([t for t, _ in plan.skipped], [low])  # low can't fit in 5 min left


class TestRecurringTasks(unittest.TestCase):
    """Verify occurs_on expands daily/weekly/monthly frequencies correctly."""

    def _task(self, frequency):
        pet = Pet(name="Max", age=3, species="dog")
        return Task(task_type="walk", pet=pet, date="2026-07-03", time="08:00",
                    frequency=frequency)

    def test_once_only_on_start_date(self):
        t = self._task("once")
        self.assertTrue(t.occurs_on("2026-07-03"))
        self.assertFalse(t.occurs_on("2026-07-04"))

    def test_daily_every_day_after_start(self):
        t = self._task("daily")
        self.assertTrue(t.occurs_on("2026-07-03"))
        self.assertTrue(t.occurs_on("2026-07-10"))
        self.assertFalse(t.occurs_on("2026-07-02"))   # never before start

    def test_weekly_every_seven_days(self):
        t = self._task("weekly")
        self.assertTrue(t.occurs_on("2026-07-10"))    # +7 days
        self.assertFalse(t.occurs_on("2026-07-06"))   # +3 days

    def test_monthly_same_day_of_month(self):
        t = self._task("monthly")
        self.assertTrue(t.occurs_on("2026-08-03"))    # same day, next month
        self.assertFalse(t.occurs_on("2026-08-04"))


class TestConflictDetection(unittest.TestCase):
    """Verify detect_conflicts flags overlapping same-pet windows on a day."""

    def test_overlapping_tasks_conflict(self):
        owner = Owner("Alice", "alice@example.com")
        pet = Pet(name="Max", age=3, species="dog")
        owner.add_pet(pet)
        schedule = Schedule(owner)

        a = Task(task_type="walk", pet=pet, date="2026-07-03", time="09:00", duration=30)
        b = Task(task_type="feeding", pet=pet, date="2026-07-03", time="09:15", duration=10)
        schedule.add_task(a)
        schedule.add_task(b)

        conflicts = schedule.detect_conflicts()
        self.assertEqual(len(conflicts), 1)

    def test_non_overlapping_tasks_do_not_conflict(self):
        owner = Owner("Alice", "alice@example.com")
        pet = Pet(name="Max", age=3, species="dog")
        owner.add_pet(pet)
        schedule = Schedule(owner)

        a = Task(task_type="walk", pet=pet, date="2026-07-03", time="09:00", duration=30)
        b = Task(task_type="feeding", pet=pet, date="2026-07-03", time="10:00", duration=10)
        schedule.add_task(a)
        schedule.add_task(b)

        self.assertEqual(schedule.detect_conflicts(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
