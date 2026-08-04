# exporters

Standard-library row exporters.

- `TableExporter(columns)` — aligned text table
- `DelimitedExporter(columns, delimiter=";")` — delimited lines
- both: `add(row)`, `count()`, `export()`

Run the tests with `pytest`.
