# digest

Cutting a long run of log entries down to something a person will read,
standard library only.

- `Entry(at, text, important)` — one entry in the run.
- `Gap(dropped)` — what stands in a digest for a run of entries left out.
- `entries_only(items)` — the entries of a digest, gaps taken out.
- `stands_for(items)` — how many entries a digest stands for.
- `must_keep(entries)` — the entries a digest holds whatever it leaves out.
- `render(items)` — a printable digest, one line per item.

Run the tests with `pytest`.
