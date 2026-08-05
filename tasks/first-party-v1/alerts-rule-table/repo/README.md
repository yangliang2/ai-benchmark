# alerts

Standard-library severity rules for monitoring events.

An event is a mapping with `service`, `status` and `latency_ms`.

- `severity(event)` — page, warn, notice or ignore
- `digest(events)` — how many events of each severity

Run the tests with `pytest`.
