# noticeboard

The village noticeboard, in the standard library alone.

- `notices.py` — a `Notice`, and `newest_first` for the order they are read in
- `paging.py` — `Paginator`, which splits a run of items into fixed-size pages
- `noticeboard.py` — `Noticeboard`, which spreads the posted notices over
  boards of `NOTICES_PER_BOARD` and prints one

Run the tests with `pytest`.
