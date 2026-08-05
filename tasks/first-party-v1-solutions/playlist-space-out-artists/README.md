# playlist

Queue-building helpers for a small listening service, standard library only.

- `Track(title, artist, seconds)` — one track.
- `total_seconds(tracks)` — how long a queue runs.
- `by_artist(tracks)` — the tracks grouped by who recorded them.
- `describe(tracks)` — a printable numbered queue.

Run the tests with `pytest`.
