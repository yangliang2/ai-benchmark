# roll

A roll of photographs and what was taken when, standard library only.

- `Photo(at, shows, mark)` — one photograph: the second of the shoot it was
  taken at, what it shows, and its mark (`""`, `"blurred"` or `"keep"`).
- `in_order(photos)` — whether the roll runs in time order.
- `gaps(photos)` — the seconds between one photo and the next.
- `marked(photos, mark)` — the photos carrying a given mark.
- `shown(photos)` — what the photos show, in order.
- `describe(photos)` — a printable line per photo.

Run the tests with `pytest`.
