# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I designed four classes with clear, separated responsibilities:

- **Task** (dataclass) — a single care activity. Holds the what (`description`), when (`time`, `due_date`), how long (`duration_minutes`), importance (`priority`), and cadence (`frequency`). Keeps its own `completed` flag and exposes one method: `mark_complete()`.
- **Pet** (dataclass) — a named animal belonging to an owner. Owns a list of `Task` objects and provides `add_task` / `remove_task` helpers so the rest of the system never directly mutates `pet.tasks`.
- **Owner** — manages a roster of `Pet` objects. Acts as the single source of truth; `get_all_tasks()` aggregates every task across every pet, which is the primary entry point the Scheduler uses.
- **Scheduler** — the algorithmic brain. Holds a reference to an `Owner` and provides every data-manipulation operation: sorting, filtering, conflict detection, recurring-task generation, and building today's schedule. Keeping this logic out of `Owner` and `Pet` follows the single-responsibility principle and makes the scheduler easy to test in isolation.

Relationships: `Owner` has many `Pet`s; each `Pet` has many `Task`s; `Scheduler` is bound to one `Owner`.

**b. Design changes**

One meaningful change from the initial sketch was separating `mark_task_complete()` on the `Scheduler` from `mark_complete()` on `Task`. My first instinct was to put recurrence logic directly inside `Task.mark_complete()`, but that would have required a `Task` to know which `Pet` it belongs to so it could append a follow-up — a circular dependency. Moving recurrence into `Scheduler.mark_task_complete()` keeps `Task` a pure data object and lets the scheduler stay in control of side effects.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:

- **Time** — tasks are sorted by `HH:MM` string so the daily view is always chronological.
- **Due date** — `get_today_schedule()` only surfaces tasks where `due_date <= today`, keeping future recurring tasks out of today's view until they are actually due.
- **Completion status** — completed tasks are excluded from the daily schedule and can be viewed separately via the filter.
- **Priority** — exposed as a filter so the owner can focus on high-priority items; it does not currently reorder within the same time slot.

Time was treated as the primary constraint because a pet owner's day is fundamentally clock-driven: walks happen in the morning, medications at fixed times, and meals on a schedule.

**b. Tradeoffs**

The conflict detector flags tasks that share an **exact** `HH:MM` string. A more sophisticated approach would compare time ranges (start time + duration) so that a 30-minute walk starting at 08:00 and a 10-minute feeding starting at 08:20 would also conflict. The exact-match approach was chosen because it is simple, transparent, and bug-free for the scope of this project. Extending it to range overlap is a clear next step using `datetime` arithmetic.

---

## 3. AI Collaboration

**a. How you used AI**

AI was used at every phase but with different roles:

- **Design** — brainstorming which class should own recurrence logic (the `Task` vs. `Scheduler` question above).
- **Scaffolding** — generating initial dataclass stubs and method signatures from the UML description.
- **Algorithmic suggestions** — proposing the `sorted(tasks, key=lambda t: t.time)` pattern for sorting and suggesting `timedelta` for recurrence date arithmetic.
- **Test generation** — drafting an initial set of pytest functions from method signatures, which I then extended with edge-case tests (idempotent completion, future-task exclusion, etc.).

The most valuable prompt pattern was asking specific "which class should own this behavior, and why?" questions rather than "write the code for me" — it produced design rationale, not just code.

**b. Judgment and verification**

An early AI suggestion placed recurrence logic inside `Task.mark_complete()` and had the method accept a `pet` argument so it could append the follow-up task directly. I rejected this because it violated the single-responsibility principle: a `Task` should not know about the container that holds it. I verified the concern by sketching a dependency diagram and confirmed the circular reference before deciding to move recurrence into `Scheduler.mark_task_complete()` instead. The AI accepted the revised framing immediately and produced a cleaner implementation.

---

## 4. Testing and Verification

**a. What you tested**

19 tests across seven behavior categories:

1. `mark_complete()` changes `completed` to `True` and is idempotent.
2. `add_task` / `remove_task` correctly mutate the pet's task list.
3. `get_all_tasks()` aggregates tasks from multiple pets.
4. `sort_by_time()` returns tasks in strict chronological order.
5. `filter_by_pet()` and `filter_by_status()` return only matching tasks.
6. Daily and weekly recurrence create a follow-up task with the correct `due_date`; one-time tasks produce no follow-up.
7. Conflict detection flags exact-time clashes and passes non-conflicting schedules.
8. `get_today_schedule()` excludes future-dated and already-completed tasks.

These tests were chosen because they cover the algorithmic behaviors (sort, filter, conflict, recurrence) that are the hardest to reason about manually and the most likely to regress during refactoring.

**b. Confidence**

Confidence: ★★★★☆

The happy paths and primary edge cases are well covered. The remaining gap is overlapping-duration conflicts (e.g., an 08:00/30-min task and an 08:15/30-min task conflict in real life but are not flagged by the current detector). I would also add tests for the Streamlit session-state wiring if a testing framework for Streamlit UI components were available.

---

## 5. Reflection

**a. What went well**

The "CLI-first" workflow (building and verifying `pawpal_system.py` through `main.py` and `pytest` before touching `app.py`) made connecting the UI trivial. Every Streamlit button click maps directly to a Scheduler method call with no guesswork.

**b. What you would improve**

The conflict detector only checks for exact time matches. I would extend it to compare time ranges using `datetime` objects, so any two tasks whose `[start, start + duration]` intervals overlap are flagged — this would make the warnings far more useful for real scheduling.

**c. Key takeaway**

The most important lesson is that AI accelerates implementation but is a poor architect. Every time I asked AI to "just write it," the result was technically correct but often violated a design principle (wrong responsibility, circular dependency, unnecessary coupling). The AI was most valuable when I had already decided *what* to build and used it to produce the *how* quickly. The architect's job — deciding where logic lives and why — remained entirely a human responsibility.
