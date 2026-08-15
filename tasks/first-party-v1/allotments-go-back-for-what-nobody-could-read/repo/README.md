# allotments

The society's standpipe readings, in the standard library alone.

- `plots.py` — a `Plot`, which of them have a standpipe on, and how a plot
  number is read off something written down
- `cards.py` — a `Card`, the figure on one, and how a card is written up in
  the book
- `ledger.py` — `Quarter`, a whole run of cards as it came back off the site,
  and `Reading`, one plot's standpipe once its card has been made out
- `society.py` — `Society`, which puts the site's plots and a run of cards
  together and makes up the sheet that goes on the wall

A card nobody can make out is not a reading. Its plot is left off the sheet
and goes on the list to go back to, and the society carries no figure for it
until a fresh card comes in.

Run the tests with `pytest`.
