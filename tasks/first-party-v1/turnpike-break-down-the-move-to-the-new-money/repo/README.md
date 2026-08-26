# The turnpike tollhouse's roll

One JSON file, `roll.json`, is the whole record: a line for every crossing
taken at the gate, with the day, the kind, the charge taken and a note where
one was worth making. `roll.py` reads and writes the file, `tariff.py` is
the table of tolls, `gate.py` is how a crossing goes onto the roll,
`till.py` is what gets read back out, and `cli.py` is how the keeper works
it:

    python cli.py cross 1926-01-04 cart --note "Marsh's dray"
    python cli.py wave  1926-01-04 foot --note "the parson"
    python cli.py takings 1926-01-04
    python cli.py count 1926-01-04
    python cli.py check
    python cli.py rates

Standard library only; there is nothing to install.
