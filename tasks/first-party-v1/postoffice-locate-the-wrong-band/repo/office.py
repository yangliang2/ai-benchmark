"""The office: where the day's parcels go when they leave, and what the day
came to.

The window takes the money and the office sends the things, and the two
readings taken off a parcel answer one question each. The sacks are packed off
the gauge — what will not go in the small sack goes in the big one, whatever it
weighs — and whether it takes two of them to carry a parcel out is the scale's
business. What a parcel was charged is the window's figure, and it is not
worked out a second time here.
"""

from counter import NOTHING_TAKEN
from parcels import size_band, weight_band

NO_NOTE = ""

SACKS = {
    "A": "the pouch",
    "B": "the small sack",
    "C": "the big sack",
    "D": "the hamper",
}

TAKES_TWO = ("C", "D")


class Office:
    """The office behind the counter, and what it has written down."""

    def __init__(self, notes=None):
        self.notes = dict(notes or {})

    def note_on(self, label):
        """Whatever the office has written against one parcel, and nothing
        where it has written nothing."""
        try:
            return self.notes[label]
        except KeyError:
            return NO_NOTE

    def sack_for(self, window, label):
        """Which sack a parcel leaves in, off what the gauge made of it."""
        return SACKS[size_band(window.parcel_for(label).inches)]

    def two_to_carry(self, window, label):
        """Whether it takes two of them to carry a parcel out to the van."""
        return weight_band(window.parcel_for(label).grams) in TAKES_TWO

    def charges(self, window):
        """Every parcel the day took in, priced up as it was charged."""
        return [window.charge_for(label) for label in window.handed_in()]

    def takings(self, window):
        """What the day came to over the counter."""
        taken = NOTHING_TAKEN
        for charge in self.charges(window):
            taken += charge.pence
        return taken

    def book(self, window):
        """The book for the day: every parcel written up as it was charged."""
        return [charge.written_up() for charge in self.charges(window)]
