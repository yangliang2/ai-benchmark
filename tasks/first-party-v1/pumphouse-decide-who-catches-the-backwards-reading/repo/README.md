# The pump-house book

One JSON file, `book.json`, is the whole record: every metered house on the
works, with the day its meter was last fitted, and a line for every visit of
the meter-reader. `ledger.py` reads and writes the file, `intake.py` is every
way the book changes, `render.py` is what gets read back out, and `cli.py` is
how the clerk works it:

    python cli.py fit   1927-03-02 mill-lane
    python cli.py read  1927-03-25 mill-lane 1400
    python cli.py read  1927-06-24 mill-lane 1721 --note "reader: J. Hale"
    python cli.py refit 1927-07-30 mill-lane
    python cli.py read  1927-09-29 mill-lane 63
    python cli.py stand
    python cli.py bill  mill-lane 1927-06-25 1927-09-29 4

Standard library only; there is nothing to install.
