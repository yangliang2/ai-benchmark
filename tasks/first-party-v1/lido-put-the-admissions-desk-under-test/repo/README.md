# lido

The borough lido's admissions desk, in the standard library alone.

- `lido.py` — `admit`, which says what one swimmer at the desk is told, and
  `roll_call`, which says it down a whole queue
- `tests/` — where the lido's tests go. There are none yet: the desk has been
  worked by hand since it opened.

A session is an hour of the water given over to one thing — a lane session, a
family session, a club session — and the desk's whole job is to say who goes
in, who waits for the next one, and who is turned away at the gate.

Run the tests with `pytest`.
