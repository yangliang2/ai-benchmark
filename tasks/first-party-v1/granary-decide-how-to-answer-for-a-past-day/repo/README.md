# The granary's book

One JSON file, `book.json`, is the whole record: what every bin holds today,
and a movement line for every delivery in and every issue out through the
door. `ledger.py` reads and writes the file, `book.py` is every way the book
changes, `report.py` is what gets read back out, and `cli.py` is how the
clerk works it:

    python cli.py open 1926-01-04 north wheat 120
    python cli.py in   1926-01-11 north 40 --note "Marsh's cart"
    python cli.py out  1926-01-12 north 25 --note "the mill"
    python cli.py set-right 1926-09-29 north 131
    python cli.py stocktake
    python cli.py movements 1926-01-01 1926-03-31

Standard library only; there is nothing to install.
