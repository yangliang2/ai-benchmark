"""Stock held as dated lots.

A lot is what one delivery brought in: the date it was received, how many
units, and what each unit cost. Lots are plain immutable records, and the
stock on hand is a tuple of them kept in the order they were received --
oldest first, and a lot received the same day as one already held goes after
it, because that is the order the stock is drawn in.

Quantities are whole numbers of units and never negative, a lot holding no
units is not a lot, and no function here conjures up stock that no delivery
brought in. Nothing here modifies the stock it is given; every function hands
back a tuple of its own.
"""

from collections import namedtuple

Lot = namedtuple("Lot", "received quantity unit_cost")


def receive(lots, lot):
    """The stock with one more lot in it, in received order.

    A delivery brings units in, so one bringing none is not a lot and the
    stock never holds one.
    """
    if lot.quantity <= 0:
        raise ValueError(f"a delivery of {lot.quantity} units is not a lot")
    position = len(lots)
    while position and lots[position - 1].received > lot.received:
        position -= 1
    return lots[:position] + (lot,) + lots[position:]


def on_hand(lots):
    """How many units of stock there are."""
    return sum(lot.quantity for lot in lots)


def value(lots):
    """What the stock on hand cost to buy."""
    return sum(lot.quantity * lot.unit_cost for lot in lots)
