"""CLI demo script: verifies PawPal+ backend logic in the terminal."""

from datetime import date, timedelta
from src.pawpal_system import Owner, Pet, Task, Scheduler


def print_section(title: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print("=" * 50)


def main() -> None:
    # ------------------------------------------------------------------ #
    # 1. Set up owner and pets
    # ------------------------------------------------------------------ #
    owner = Owner("Jordan")

    mochi = Pet("Mochi", "dog")
    luna = Pet("Luna", "cat")

    owner.add_pet(mochi)
    owner.add_pet(luna)

    # ------------------------------------------------------------------ #
    # 2. Add tasks (intentionally out of order to test sorting)
    # ------------------------------------------------------------------ #
    today = date.today()

    mochi.add_task(Task("Evening walk",    "18:30", 45, "high",   "daily",  "Mochi", today))
    mochi.add_task(Task("Morning walk",    "07:00", 30, "high",   "daily",  "Mochi", today))
    mochi.add_task(Task("Heartworm pill",  "08:00",  5, "high",   "once",   "Mochi", today))
    mochi.add_task(Task("Afternoon fetch", "14:00", 20, "medium", "once",   "Mochi", today))

    luna.add_task(Task("Wet food",         "08:00", 10, "high",   "daily",  "Luna",  today))
    luna.add_task(Task("Brush coat",       "10:00", 15, "medium", "weekly", "Luna",  today))
    luna.add_task(Task("Litter box clean", "12:00", 10, "medium", "daily",  "Luna",  today))

    scheduler = Scheduler(owner)

    # ------------------------------------------------------------------ #
    # 3. Print today's sorted schedule
    # ------------------------------------------------------------------ #
    print_section("TODAY'S SCHEDULE")
    schedule = scheduler.get_today_schedule()
    if schedule:
        for task in schedule:
            print(f"  {task}")
    else:
        print("  No tasks due today.")

    # ------------------------------------------------------------------ #
    # 4. Detect conflicts (Mochi's heartworm pill and Luna's wet food clash)
    # ------------------------------------------------------------------ #
    print_section("CONFLICT WARNINGS")
    warnings = scheduler.get_conflict_warnings()
    if warnings:
        for w in warnings:
            print(f"  ⚠  {w}")
    else:
        print("  No conflicts detected.")

    # ------------------------------------------------------------------ #
    # 5. Filter by pet
    # ------------------------------------------------------------------ #
    print_section("MOCHI'S TASKS ONLY")
    for task in scheduler.sort_by_time(scheduler.filter_by_pet("Mochi")):
        print(f"  {task}")

    # ------------------------------------------------------------------ #
    # 6. Mark a recurring task complete — should spawn a follow-up
    # ------------------------------------------------------------------ #
    print_section("MARK 'MORNING WALK' COMPLETE (daily → recurs tomorrow)")
    morning_walk = next(t for t in mochi.tasks if t.description == "Morning walk")
    next_task = scheduler.mark_task_complete(morning_walk.id)
    print(f"  Completed: {morning_walk}")
    if next_task:
        print(f"  Next occurrence created: {next_task} (due {next_task.due_date})")

    # ------------------------------------------------------------------ #
    # 7. Show remaining incomplete tasks
    # ------------------------------------------------------------------ #
    print_section("REMAINING INCOMPLETE TASKS")
    incomplete = scheduler.filter_by_status(completed=False)
    for task in scheduler.sort_by_time(incomplete):
        print(f"  {task}")

    print()


if __name__ == "__main__":
    main()
