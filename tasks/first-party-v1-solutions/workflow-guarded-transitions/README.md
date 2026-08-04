# workflow

A minimal finite-state machine and the ticket workflow built on it,
standard library only.

- `fsm.Machine(initial, transitions)` — fire events, follow the table
- `tickets.new_ticket()` — new -> triaged -> in-progress -> done

Run the tests with `pytest`.
