# cornexchange

A corn exchange punches the day's calls onto one ticker tape and, when the
floor empties, reckons the best turn the day offered: buy at one call,
sell at a later one.

- `tape.py` — the tape itself. Reading a call back means winding the punch
  under the glass, and the tape tallies every winding: each one stretches
  the paper, and the house has always kept the count.
- `floor.py` — the reckoning. `Floor.best_turn` names the hour to have
  bought, the hour to have sold, and the gain.

Run the tests with `pytest`.
