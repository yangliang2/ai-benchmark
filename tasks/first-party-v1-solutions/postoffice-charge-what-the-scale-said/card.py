"""The card on the wall: what a parcel costs to send.

The card is a run of bands with a price against each, in pence. Which line of
it a parcel is charged at is settled by what the parcel weighed: the office has
priced by the scale since the day it opened, and what the gauge makes of a
parcel has never had anything to do with the money. The gauge answers the other
question the counter asks — how much room the thing takes up when it leaves —
and the sacks are packed on its answer. What is paid over the counter comes off
this card against the scale's band, and against no other reading.

A band this card carries no price against is not a parcel that goes free: the
card says so outright rather than charging the nearest thing to it.
"""

POSTAGE = {"A": 165, "B": 235, "C": 340, "D": 495}


class NotOnTheCard(ValueError):
    """The card carries no price against that band."""


def to_pay(band):
    """What the card says against one band, in pence."""
    try:
        return POSTAGE[band]
    except KeyError:
        raise NotOnTheCard(band) from None


def written_as(pence):
    """What money looks like written up in the book: `£3.40`."""
    return f"£{pence // 100}.{pence % 100:02d}"
