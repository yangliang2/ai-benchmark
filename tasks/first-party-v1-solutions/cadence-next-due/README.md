# cadence

When a repeating job is due to run. Times are whole seconds on one clock —
no calendars, no time zones. Standard library only.

- `make(name, first_due, every)` — a schedule.
- `slots(schedule, count)` — the first `count` times the job is due.
- `is_a_slot(schedule, when)` — whether a time is one of them.
- `overran_by(schedule, due_at, ran_at)` — how far past its slot a run went.
- `describe(schedule)` — a printable line.

Run the tests with `pytest`.
