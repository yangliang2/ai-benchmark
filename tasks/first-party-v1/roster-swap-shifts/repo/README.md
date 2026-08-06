# roster

The on-call rota for a small team: one shift a day, and whoever is on it.
Standard library only.

- `new_roster(days)` — a roster with a shift a day and nobody on any of them.
- `days(roster)` — the roster's days, in order.
- `who_is_on(roster, day)` — the people on that day's shift, in order.
- `add_shift(roster, day, name)` / `drop_shift(roster, day, name)` — put
  someone on a shift, or take them off it.
- `describe(roster)` — one printable line per day.

Run the tests with `pytest`.
