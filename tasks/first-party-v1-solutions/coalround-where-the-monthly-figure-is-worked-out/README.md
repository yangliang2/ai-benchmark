# The coal round

One cart, one lane, and a book kept in pencil. The yard sends the cart out
through the season and asks each house for what it had at the end of every
month.

- `grades.py` — the kinds of coal, and what a single sack of a kind fetches
  in a given month.
- `deliveries.py` — what went in at which door, in which month, and how far
  out the door stands. Quantities only.
- `statement.py` — the terms the yard trades on, and what one house is asked
  for at the end of one month.

The first two hold the pieces and neither of them multiplies anything by
anything; the third is where the pieces meet the terms.

Run the tests with `pytest`. Nothing outside the standard library is needed.
