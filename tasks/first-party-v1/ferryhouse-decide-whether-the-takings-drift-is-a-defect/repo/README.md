# The ferry-house box

One JSON file, `book.json`, is the whole record: the fare for each class of
crossing as it stands, and a line for every crossing made and every crossing
turned back. `ledger.py` reads and writes the file, `fares.py` and
`crossings.py` are every way the book changes, `report.py` is what gets read
back out, and `cli.py` is how the clerk works it:

    python cli.py fare horse 4
    python cli.py quote horse
    python cli.py cross 1929-04-11 horse --note "Marsh's mare"
    python cli.py refund 1929-04-11 horse --note "ice; turned back"
    python cli.py takings 1929-03-25 1929-06-23
    python cli.py tally 1929-03-25 1929-06-23

Standard library only; there is nothing to install.
