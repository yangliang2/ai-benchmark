# cooperage

A small cooperage keeps its casks on a rack and quotes the day's order book
off it: for each order, the snuggest cask that holds it.

- `gauging.py` — the shop's gauging rod. Gauging a cask reads its capacity
  in whole gallons, and the gauge tallies every gauging: each one means a
  walk to the rack and a cask open to the air, so the shop has always kept
  the count.
- `rack.py` — the rack itself. `Rack.cask_for` finds the snuggest cask for
  one order; `Rack.quote` answers the whole book, in the order it was taken.

Run the tests with `pytest`.
