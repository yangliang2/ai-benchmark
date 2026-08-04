# spendreport

A standard-library spending report over "name,cents" expense files.

- `storage.load_entries(path)` — parse one expense file
- `analysis.summarise(...)` / `analysis.over_budget(...)` — the numbers
- `cli.report(path, budget_cents)` — the full report

Run the tests with `pytest`.
