# cartons

Despatch-side packing helpers, standard library only.

- `Item(sku, weight)` — one thing to ship, weighed in grams.
- `total_weight(carton)` — what a carton weighs.
- `fits(carton, item, capacity)` — whether one more item can go in.
- `manifest(cartons)` — a printable summary of a despatch.

Run the tests with `pytest`.
