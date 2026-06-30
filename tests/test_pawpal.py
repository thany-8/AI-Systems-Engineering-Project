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


if __name__ == "__main__":
    unittest.main(verbosity=2)
