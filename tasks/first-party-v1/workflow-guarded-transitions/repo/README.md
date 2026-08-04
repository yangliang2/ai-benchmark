# workflow

A standard-library finite-state machine and the ticket workflow built on it.

- `fsm.Machine(initial, transitions)` — fire events, follow the table
- `tickets.new_ticket()` — new -> triaged -> in-progress -> done

Run the tests with `pytest`.
