"""A day at the counter: what came over it, and what was charged for it.

`Charge` is one parcel priced up, and `Window` is a day's worth of them in the
order they were handed in.

The window's business is the money: it is here that what a parcel costs to send
comes off the card on the wall, and the figure goes from here to the office.
Where a parcel goes after that — which sack it leaves in, and who carries it
out — is the office's business and is settled there.
"""

from typing import NamedTuple

from card import to_pay, written_as
from parcels import weight_band

NOTHING_TAKEN = 0


class Charge(NamedTuple):
    """One parcel priced up: the label it came in under, and what was paid."""

    label: str
    pence: int

    def written_up(self):
        """How a charge goes down in the book: the label, and the money."""
        return f"{self.label}: {written_as(self.pence)}"


def most_charged(charges):
    """The parcel that cost the most of any taken in on one day."""
    return max(charges, key=lambda charge: charge.pence, default=None)


class Window:
    """A day at the counter, as the parcels came over it."""

    def __init__(self, parcels):
        self.parcels = {parcel.label: parcel for parcel in parcels}

    def handed_in(self):
        """The labels the day's parcels came in under, in the order they came
        over."""
        return list(self.parcels)

    def parcel_for(self, label):
        """The parcel taken in under one label, as it was written down."""
        return self.parcels[label]

    def weighed(self, label):
        """The band the scale put one parcel in."""
        return weight_band(self.parcel_for(label).grams)

    def postage_on(self, label):
        """What one parcel comes to, off the card on the wall."""
        return to_pay(weight_band(self.parcel_for(label).grams))

    def charge_for(self, label):
        """One parcel priced up, ready for the book."""
        return Charge(label, self.postage_on(label))
