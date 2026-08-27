# The maltings steep-house log

One file, `steeplog.jsonl`, is the whole record: a line for every working
the house takes — barley steeped, a floor turned, a kilning drawn off —
with the day, the working, the quarters it moved and the pit or floor it
touched. `log.py` reads and writes the file, `floorwork.py` is how a
working goes onto the log, `reckon.py` is what gets read back out,
`monthend.py` carries a finished month to the maltster's ledger, and
`cli.py` is how the steward works it:

    python cli.py steep 1926-10-02 4 --pit 1
    python cli.py turn 1926-10-05 4 --floor 2
    python cli.py kiln 1926-10-12 4
    python cli.py day 1926-10-02
    python cli.py standing
    python cli.py carry 1926-10

Standard library only; there is nothing to install.
