# logparse

Standard-library readers for timestamped log lines.

- `entry_level(line)` — the level token of one line
- `entry_message(line)` — the message after the level, verbatim
- `entries_between(lines, start, end)` — remainders of lines inside a window

Run the tests with `pytest`.
