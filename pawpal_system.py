"""PawPal+ backend logic: Owner, Pet, Task, and Scheduler classes."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional
import uuid


@dataclass
class Task:
    """Represents a single pet care activity."""

    description: str
    time: str  # "HH:MM" 24-hour format
    duration_minutes: int
    priority: str  # "low", "medium", "high"
    frequency: str  # "once", "daily", "weekly"
    pet_name: str
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        return (
            f"[{status}] {self.time} — {self.description} "
            f"({self.pet_name}, {self.duration_minutes}min, {self.priority})"
        )


@dataclass
class Pet:
    """Stores pet details and its list of tasks."""

    name: str
    species: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID. Returns True if found and removed."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]
        return len(self.tasks) < before

    def __str__(self) -> str:
        return f"{self.name} ({self.species})"


class Owner:
    """Manages multiple pets and provides access to all their tasks."""

    def __init__(self, name: str) -> None:
        """Initialize an owner with a name and empty pet list."""
        self.name = name
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's roster."""
        self.pets.append(pet)

    def get_pet(self, name: str) -> Optional[Pet]:
        """Retrieve a pet by name (case-insensitive)."""
        for pet in self.pets:
            if pet.name.lower() == name.lower():
                return pet
        return None

    def get_all_tasks(self) -> List[Task]:
        """Return every task across all pets."""
        tasks: List[Task] = []
        for pet in self.pets:
            tasks.extend(pet.tasks)
        return tasks

    def __str__(self) -> str:
        return f"Owner: {self.name} ({len(self.pets)} pet(s))"


class Scheduler:
    """The brain that retrieves, organises, and manages tasks across pets."""

    def __init__(self, owner: Owner) -> None:
        """Bind the scheduler to an owner instance."""
        self.owner = owner

    # ------------------------------------------------------------------
    # Sorting & filtering
    # ------------------------------------------------------------------

    def sort_by_time(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        """Return tasks sorted chronologically by their HH:MM time string."""
        if tasks is None:
            tasks = self.owner.get_all_tasks()
        return sorted(tasks, key=lambda t: t.time)

    def filter_by_pet(self, pet_name: str) -> List[Task]:
        """Return all tasks belonging to a specific pet."""
        return [
            t for t in self.owner.get_all_tasks()
            if t.pet_name.lower() == pet_name.lower()
        ]

    def filter_by_status(self, completed: bool) -> List[Task]:
        """Return tasks matching the given completion status."""
        return [t for t in self.owner.get_all_tasks() if t.completed == completed]

    def filter_by_priority(self, priority: str) -> List[Task]:
        """Return tasks matching the given priority level."""
        return [
            t for t in self.owner.get_all_tasks()
            if t.priority.lower() == priority.lower()
        ]

    # ------------------------------------------------------------------
    # Daily schedule
    # ------------------------------------------------------------------

    def get_today_schedule(self) -> List[Task]:
        """Return incomplete tasks due today or earlier, sorted by time."""
        today = date.today()
        due = [
            t for t in self.owner.get_all_tasks()
            if t.due_date <= today and not t.completed
        ]
        return self.sort_by_time(due)

    # ------------------------------------------------------------------
    # Recurring tasks
    # ------------------------------------------------------------------

    def mark_task_complete(self, task_id: str) -> Optional[Task]:
        """Mark a task complete and create the next occurrence for recurring tasks.

        Returns the newly created follow-up Task, or None for one-time tasks.
        """
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.id == task_id:
                    task.mark_complete()
                    if task.frequency == "daily":
                        next_due = task.due_date + timedelta(days=1)
                    elif task.frequency == "weekly":
                        next_due = task.due_date + timedelta(weeks=1)
                    else:
                        return None  # one-time task — no follow-up needed

                    next_task = Task(
                        description=task.description,
                        time=task.time,
                        duration_minutes=task.duration_minutes,
                        priority=task.priority,
                        frequency=task.frequency,
                        pet_name=task.pet_name,
                        due_date=next_due,
                    )
                    pet.add_task(next_task)
                    return next_task
        return None

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self, tasks: Optional[List[Task]] = None) -> List[tuple]:
        """Return pairs of tasks scheduled at the exact same time."""
        if tasks is None:
            tasks = self.get_today_schedule()
        conflicts: List[tuple] = []
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                if tasks[i].time == tasks[j].time:
                    conflicts.append((tasks[i], tasks[j]))
        return conflicts

    def get_conflict_warnings(self) -> List[str]:
        """Return human-readable warning strings for every detected conflict."""
        warnings: List[str] = []
        for t1, t2 in self.detect_conflicts():
            warnings.append(
                f"Conflict at {t1.time}: '{t1.description}' ({t1.pet_name}) "
                f"clashes with '{t2.description}' ({t2.pet_name})"
            )
        return warnings
