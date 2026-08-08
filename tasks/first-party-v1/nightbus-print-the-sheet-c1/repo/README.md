# nightbus

Standard-library helpers for a night-bus depot's trips. A trip is a `Trip`
— route, departure moment, running time in minutes — and a moment is a
`datetime`.

- `Trip(route, departs, minutes)` — one trip
- `arrives(trip)` — the moment it gets in
- `operating_day(moment)` — the day's working a moment belongs to
- `runs_on(trip, day)` — whether a trip belongs to that day's working
- `first_off(trips, day)` — the first of them to leave on that day's working
- `running_time(trips)` — how many minutes they take between them
- `describe(trip)` — a one-line summary

Run the tests with `pytest`.
