# cloakroom

A theatre cloakroom pegs every coat on one rail and hands them back over
the hatch: for each ticket presented, the coat checked under it.

- `pegs.py` — the rail itself. The ticket is pinned inside each coat's
  collar, so reading one means a take-down, and the rail tallies every
  take-down: each one is a handling, and the house rules have the
  attendant keep the count. One ticket to one coat.
- `cloakroom.py` — the hatch. `Cloakroom.coat_for` finds the coat for one
  ticket; `Cloakroom.hand_back` answers the whole queue, in the order it
  formed.

Run the tests with `pytest`.
