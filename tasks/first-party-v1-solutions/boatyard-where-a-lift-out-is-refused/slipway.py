"""The slipway, and the water the crane needs before it will lift.

The crane is bolted to the head of the slipway and cannot reach a keel that
is sitting too low. So the book of tides is consulted for the depth at high
water, and a day that is not in the book is not a day the crane is set up on.
This module answers that one question and no other: it does not know what is
in the store, what standings there are, or how long anybody wants to stay.
"""

# What the crane needs under a keel before it will lift at all, in centimetres.
WORKING_DEPTH_CM = 180


class Tide:
    """One day's high water: the day, and how deep it comes."""

    def __init__(self, day, depth_cm):
        self.day = day
        self.depth_cm = depth_cm

    def __repr__(self):
        return f"Tide({self.day!r}, {self.depth_cm!r})"


def workable(tides, day):
    """Whether the crane could lift on this day at all.

    A day the book says nothing about is not workable: the crane is never set
    up on a guess.
    """
    for tide in tides:
        if tide.day == day:
            return tide.depth_cm >= WORKING_DEPTH_CM
    return False
