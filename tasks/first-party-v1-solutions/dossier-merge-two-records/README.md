# dossier

What several systems separately know about one customer, standard library
only.

- `Dossier(source, seen, fields)` — one system's record: where it came from,
  when that system last saw the customer, and what it holds.
- `FIELDS` — every field a dossier can hold.
- `ADDRESS` — the three fields that are one thing between them.
- `value(dossier, field)` — what one dossier holds for one field, or None.
- `known(dossier)` — the fields it holds something for.
- `disagree(one, other, fields)` — the fields two of them hold differently.
- `describe(dossier)` — a printable summary.

Run the tests with `pytest`.
