# The tram shed

One JSON file, `book.json`, is the day's record: every working the shed
has chalked up — a car, the end of the line it runs from, and the time
it leaves, kept exactly as the foreman chalks it.

`shedbook.py` reads and writes the book, `boards.py` sets the two
departure boards — one for the town end, one for the quay end — and
`cli.py` is how the shed works it:

    python cli.py enter 14 town 4:25
    python cli.py town
    python cli.py quay
    python cli.py book

Standard library only; there is nothing to install.
