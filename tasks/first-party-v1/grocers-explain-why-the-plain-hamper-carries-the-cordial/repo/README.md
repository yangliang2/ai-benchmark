# The grocer's back room

One JSON file, `orders.json`, is the day's order book: every hamper the
shop has been asked to make up, in the order the orders came in. An
order with its own `wants` list is bespoke; any other order is for the
standard hamper. An order may carry `extras` — items slipped in on top
of whatever the hamper holds.

`hampers.py` is where a hamper is packed, `docket.py` writes the docket
that rides in the basket, and `cli.py` is how the back room works the
book:

    python cli.py book
    python cli.py make-up

Standard library only; there is nothing to install.
