# lost property

The station's lost property office, in the standard library alone.

- `handins.py` — a `Handin`, the order the desk deals with them in, and the
  ticket tied to a thing while the office is holding it
- `sorting.py` — `Desk`, which settles one thing at a time, and `Piles`, what
  an evening's sorting comes to
- `office.py` — `Office`, which puts a day's holdings and a desk together and
  writes the evening up in the book

Everything is settled once and written up as it was settled: what its owner
has been in for has gone back to them, what will not keep is thrown out that
evening whatever else is true of it, what has been here longer than the office
keeps things goes to the sale room, and the rest is on the shelf.

Run the tests with `pytest`.
