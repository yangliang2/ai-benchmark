# duration

Standard-library helpers for durations written the way people write them:
`1h 30m`, `2d 4h 15m`.

- `UNITS` — the units a duration is written in, largest first
- `unit_seconds(unit)` — how many seconds one unit is worth
- `format_duration(seconds)` — a duration written out

Units are read without regard to case, and text that is not a duration
written that way is refused rather than half-understood.

Run the tests with `pytest`.
