# The ropewalk

One JSON file, `yard.json`, is the whole record: the yarn bundles standing
on the rack, the dispatch book of every coil that has left the yard, and
the number the next tag will carry. `stores.py` reads and writes the file
and keeps the rack, `counter.py` is where an order is taken, `walk.py` is
the walk itself, `book.py` is the dispatch book, and `cli.py` is how the
clerk works it:

    python cli.py put-up "Marsh's flax" 300
    python cli.py order Trelawney 50 hawser
    python cli.py rack
    python cli.py book

Standard library only; there is nothing to install.
