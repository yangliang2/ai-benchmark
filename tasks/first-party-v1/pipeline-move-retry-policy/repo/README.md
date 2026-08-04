# pipeline

A standard-library step pipeline with retries.

- `Pipeline.add(name, step)` — append a named step
- `Pipeline.run(value)` — thread a value through every step
- `RetryPolicy(attempts, backoff_s)` — how failing steps are retried

Run the tests with `pytest`.
