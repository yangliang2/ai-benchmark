# playbill

The setting of the theatre's playbill, in the standard library alone.

- `playbill.py` — `set_bill`, which sets a piece of text into lines of a
  fixed measure, and `centre`, which stands one line in the middle of it
- `tests/` — where the printer's tests go. There are none yet: the bill has
  been set by eye since the house opened.

The measure is the width of the column the bill is printed in, counted in
characters. A word is never broken across two lines: the printer would rather
run a line over the measure than hyphenate an actress's name.

Run the tests with `pytest`.
