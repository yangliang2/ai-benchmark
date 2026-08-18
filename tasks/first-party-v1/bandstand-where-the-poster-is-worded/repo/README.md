# The bandstand

The committee books bands for the bandstand on the promenade every Sunday
afternoon through the summer, and puts a poster up on the railings saying who
is on when.

- `bands.py` — the bands themselves, and how one band's own name is set down.
- `diary.py` — what is booked and for which afternoon; dates and order, no
  words.
- `sheet.py` — the poster: what sits under each date, and how the season is
  broken into the columns the printer sets.

The first two supply the pieces and neither of them makes a phrase; the
poster is where the pieces are put together into something a passer-by reads.

Run the tests with `pytest`. Nothing outside the standard library is needed.
