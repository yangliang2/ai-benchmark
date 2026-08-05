# stockroom

Standard-library shelving for a small stockroom: a mapping from shelf name to
the list of items on that shelf.

- `place(shelves, item, shelf)` — put an item on a shelf
- `remove(shelves, item, shelf)` — take an item off a shelf
- `relabel(shelves, shelf, name)` — rename a shelf
- `move(shelves, item, source, target)` — move an item between shelves

Run the tests with `pytest`.
