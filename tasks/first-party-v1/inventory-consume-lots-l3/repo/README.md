# inventory

Standard-library helpers for stock held as dated lots.

- `Lot(received, quantity, unit_cost)` — what one delivery brought in
- `receive(lots, lot)` — the stock with one more lot in it, in received order
- `on_hand(lots)` — how many units of stock there are
- `value(lots)` — what the stock on hand cost to buy

The stock is kept in the order it was received, which is the order it is
drawn in. Nothing here modifies the stock it is given.

Run the tests with `pytest`.
