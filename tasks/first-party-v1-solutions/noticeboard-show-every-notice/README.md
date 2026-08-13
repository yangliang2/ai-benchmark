# noticeboard

The village noticeboard, in the standard library alone.

- `notices.py` — a `Notice`, and `newest_first` for the order they are read in
- `paging.py` — `Paginator`, which splits a run of items into pages of a bounded
  length, and the page arithmetic it is cut with
- `noticeboard.py` — `Noticeboard`, which spreads the posted notices over
  boards of `NOTICES_PER_BOARD` and prints one

Nothing that was posted should drop off the end: the boards take the notices
one after another, and the final board is allowed to be a short one.

Run the tests with `pytest`.
