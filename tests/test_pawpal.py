"""Automated test suite for PawPal+ scheduling logic."""

import pytest
from datetime import date, timedelta

from pawpal_system import Task, Pet, Owner, Scheduler


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def make_task(description="Walk", time="08:00", priority="high",
              frequency="once", pet_name="Mochi", days_offset=0) -> Task:
    return Task(
        description=description,
        time=time,
        duration_minutes=30,
        priority=priority,
        frequency=frequency,
        pet_name=pet_name,
        due_date=date.today() + timedelta(days=days_offset),
    )


def make_owner_with_pet() -> tuple[Owner, Pet, Scheduler]:
    owner = Owner("Jordan")
    pet = Pet("Mochi", "dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    return owner, pet, scheduler


# ------------------------------------------------------------------ #
# Task tests
# ------------------------------------------------------------------ #

def test_mark_complete_changes_status():
    """Calling mark_complete() flips completed from False to True."""
    task = make_task()
    assert not task.completed
    task.mark_complete()
    assert task.completed


def test_mark_complete_is_idempotent():
    """Calling mark_complete() twice should not raise and status stays True."""
    task = make_task()
    task.mark_complete()
    task.mark_complete()
    assert task.completed


# ------------------------------------------------------------------ #
# Pet tests
# ------------------------------------------------------------------ #

def test_add_task_increases_count():
    """Adding a task to a Pet increases its task list by one."""
    pet = Pet("Mochi", "dog")
    assert len(pet.tasks) == 0
    pet.add_task(make_task())
    assert len(pet.tasks) == 1


def test_remove_task_decreases_count():
    """Removing a task by ID reduces the pet's task count."""
    pet = Pet("Mochi", "dog")
    task = make_task()
    pet.add_task(task)
    result = pet.remove_task(task.id)
    assert result is True
    assert len(pet.tasks) == 0


def test_remove_nonexistent_task_returns_false():
    pet = Pet("Mochi", "dog")
    assert pet.remove_task("nonexistent") is False


# ------------------------------------------------------------------ #
# Owner tests
# ------------------------------------------------------------------ #

def test_get_all_tasks_aggregates_across_pets():
    """Owner.get_all_tasks() returns tasks from every pet."""
    owner = Owner("Jordan")
    dog = Pet("Mochi", "dog")
    cat = Pet("Luna", "cat")
    owner.add_pet(dog)
    owner.add_pet(cat)

    dog.add_task(make_task("Walk", pet_name="Mochi"))
    cat.add_task(make_task("Feed", pet_name="Luna"))

    assert len(owner.get_all_tasks()) == 2


def test_get_pet_returns_none_for_missing_pet():
    owner = Owner("Jordan")
    assert owner.get_pet("Ghost") is None


# ------------------------------------------------------------------ #
# Scheduler — sorting
# ------------------------------------------------------------------ #

def test_sort_by_time_returns_chronological_order():
    """sort_by_time() returns tasks in ascending HH:MM order."""
    owner, pet, scheduler = make_owner_with_pet()
    pet.add_task(make_task("Dinner",       time="18:00"))
    pet.add_task(make_task("Morning walk", time="07:00"))
    pet.add_task(make_task("Meds",         time="12:00"))

    sorted_tasks = scheduler.sort_by_time()
    times = [t.time for t in sorted_tasks]
    assert times == sorted(times)


def test_sort_by_time_stable_with_single_task():
    owner, pet, scheduler = make_owner_with_pet()
    pet.add_task(make_task())
    assert len(scheduler.sort_by_time()) == 1


# ------------------------------------------------------------------ #
# Scheduler — filtering
# ------------------------------------------------------------------ #

def test_filter_by_pet_returns_only_matching_tasks():
    owner = Owner("Jordan")
    dog = Pet("Mochi", "dog")
    cat = Pet("Luna", "cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    dog.add_task(make_task(pet_name="Mochi"))
    cat.add_task(make_task(pet_name="Luna"))

    scheduler = Scheduler(owner)
    mochi_tasks = scheduler.filter_by_pet("Mochi")
    assert all(t.pet_name == "Mochi" for t in mochi_tasks)
    assert len(mochi_tasks) == 1


def test_filter_by_status_incomplete():
    owner, pet, scheduler = make_owner_with_pet()
    t1 = make_task("Walk")
    t2 = make_task("Feed")
    t2.mark_complete()
    pet.add_task(t1)
    pet.add_task(t2)

    incomplete = scheduler.filter_by_status(completed=False)
    assert len(incomplete) == 1
    assert incomplete[0].description == "Walk"


# ------------------------------------------------------------------ #
# Scheduler — recurring tasks
# ------------------------------------------------------------------ #

def test_daily_recurrence_creates_next_day_task():
    """Completing a daily task spawns a new task for the following day."""
    owner, pet, scheduler = make_owner_with_pet()
    today = date.today()
    task = make_task("Walk", frequency="daily", days_offset=0)
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(task.id)

    assert task.completed
    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert not next_task.completed
    assert len(pet.tasks) == 2


def test_weekly_recurrence_creates_next_week_task():
    """Completing a weekly task spawns a new task seven days later."""
    owner, pet, scheduler = make_owner_with_pet()
    today = date.today()
    task = make_task("Grooming", frequency="weekly")
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(task.id)

    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_once_task_does_not_recur():
    """Completing a one-time task returns None (no follow-up created)."""
    owner, pet, scheduler = make_owner_with_pet()
    task = make_task(frequency="once")
    pet.add_task(task)

    result = scheduler.mark_task_complete(task.id)

    assert result is None
    assert len(pet.tasks) == 1  # no new task created


# ------------------------------------------------------------------ #
# Scheduler — conflict detection
# ------------------------------------------------------------------ #

def test_conflict_detected_for_same_time():
    """Two tasks at the same time for the same day trigger a conflict."""
    owner, pet, scheduler = make_owner_with_pet()
    today = date.today()
    pet.add_task(Task("Walk",    "09:00", 30, "high",   "once", "Mochi", today))
    pet.add_task(Task("Feeding", "09:00", 10, "medium", "once", "Mochi", today))

    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) == 1


def test_no_conflict_for_different_times():
    owner, pet, scheduler = make_owner_with_pet()
    today = date.today()
    pet.add_task(Task("Walk",    "09:00", 30, "high",   "once", "Mochi", today))
    pet.add_task(Task("Feeding", "10:00", 10, "medium", "once", "Mochi", today))

    assert scheduler.detect_conflicts() == []


def test_conflict_warning_message_format():
    """get_conflict_warnings() returns non-empty strings for conflicts."""
    owner, pet, scheduler = make_owner_with_pet()
    today = date.today()
    pet.add_task(Task("Walk",    "09:00", 30, "high", "once", "Mochi", today))
    pet.add_task(Task("Feeding", "09:00", 10, "high", "once", "Mochi", today))

    warnings = scheduler.get_conflict_warnings()
    assert len(warnings) == 1
    assert "09:00" in warnings[0]


# ------------------------------------------------------------------ #
# Scheduler — today's schedule
# ------------------------------------------------------------------ #

def test_today_schedule_excludes_future_tasks():
    owner, pet, scheduler = make_owner_with_pet()
    tomorrow = date.today() + timedelta(days=1)
    pet.add_task(make_task("Future walk", days_offset=1))

    assert scheduler.get_today_schedule() == []


def test_today_schedule_excludes_completed_tasks():
    owner, pet, scheduler = make_owner_with_pet()
    task = make_task(days_offset=0)
    task.mark_complete()
    pet.add_task(task)

    assert scheduler.get_today_schedule() == []
