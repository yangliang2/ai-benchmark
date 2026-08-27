# The almshouse day-book

One JSON file, `book.json`, is the whole record: an entry for every dole
handed out at the door, with the day, who it went to, the kind of dole and a
note where one was worth making. `book.py` reads and writes the file,
`basket.py` is the table of doles, `door.py` is how a dole goes into the
book, `tally.py` is what gets read back out, and `cli.py` is how the clerk
works it:

    python cli.py give 1926-09-29 "Widow Hartley" bread
    python cli.py give 1926-09-29 "Old Tunnicliffe" coal --note "young Tunnicliffe fetched it"
    python cli.py refuse 1926-09-29 "Widow Hartley" bread --note "already helped this week"
    python cli.py day 1926-09-29
    python cli.py history "Widow Hartley"
    python cli.py often
    python cli.py doles

Standard library only; there is nothing to install.
