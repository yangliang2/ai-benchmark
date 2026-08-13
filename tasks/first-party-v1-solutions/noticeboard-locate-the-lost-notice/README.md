# noticeboard

The village noticeboard, in the standard library alone.

- `notices.py` — a `Notice`, and `newest_first` for the order they are read in
- `paging.py` — `Paginator`, which splits a run of items into fixed-size pages,
  and the page arithmetic it is cut with
- `noticeboard.py` — `Noticeboard`, which spreads the posted notices over
  boards of `NOTICES_PER_BOARD` and prints one

Nothing that was posted is meant to fall off the end: the boards fill up in
order, and the last one carries however few notices are left over.

Run the tests with `pytest`.
