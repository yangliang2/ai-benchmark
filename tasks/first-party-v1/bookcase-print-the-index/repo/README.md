# bookcase

A run of books and the shelves they have to go on, standard library only.

- `Book(title, subject, width)` — one book, its width in millimetres.
- `span(books)` — how much shelf a stretch of books takes up.
- `runs(books)` — the run broken into stretches of one subject.
- `titles(books)` — the titles of a stretch, in the order they stand.
- `subjects(books)` — the subjects the run covers, once each.
- `describe(shelves)` — a printable line per shelf.

Run the tests with `pytest`.
