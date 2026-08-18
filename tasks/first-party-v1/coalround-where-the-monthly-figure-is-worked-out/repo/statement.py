"""What one house owes for one month.

`grades.price_of` says what a single sack of a kind fetches, and
`deliveries.Round` says what went in at a door and how far out that door
stands. Neither of them multiplies anything by anything, and neither knows
the terms the yard trades on. The arithmetic that puts the one to the other
is done in this module and in no other.
"""

from grades import price_of


class Terms:
    """The terms the yard trades on: what it charges for the outlying houses,
    what it allows for a sack handed back, the smallest sum it will take from
    a house that had anything at all, and how far out a house must lie to
    count as outlying."""

    def __init__(self, carriage, allowed_back, least, near_miles):
        self.carriage = carriage
        self.allowed_back = allowed_back
        self.least = least
        self.near_miles = near_miles

    def __repr__(self):
        return (
            f"Terms({self.carriage!r}, {self.allowed_back!r}, {self.least!r}, "
            f"{self.near_miles!r})"
        )


# What the yard has traded on since the war, and what it uses unless told
# otherwise.
USUAL = Terms(carriage=30, allowed_back=2, least=250, near_miles=3)


class Statement:
    """One season's monthly reckonings, taken off one round on one set of
    terms."""

    def __init__(self, round_, terms=USUAL):
        self.round = round_
        self.terms = terms

    def made_up(self, house, month):
        """What this house owes for this month, in pence."""
        had = self.round.at(house, month)
        if not had:
            return 0
        owed = sum(
            delivery.sacks * price_of(delivery.grade, month) for delivery in had
        )
        owed -= sum(delivery.empties for delivery in had) * self.terms.allowed_back
        if house.miles > self.terms.near_miles:
            owed += self.terms.carriage
        return max(owed, self.terms.least)

    def season(self, house):
        """What this house owes over the whole season, in pence."""
        return sum(
            self.made_up(house, month) for month in self.round.months(house)
        )
