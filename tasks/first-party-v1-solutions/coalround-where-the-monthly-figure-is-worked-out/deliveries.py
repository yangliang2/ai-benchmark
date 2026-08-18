"""What was dropped at which door, and in which month.

The round holds quantities and nothing else: it will say what a house had in
a month, in the order the man wrote it down, and which months a house had
anything at all. It knows how far out a house stands because the man who
wrote it down had to go there, and it prices nothing whatever.
"""


class House:
    """A house on the round: what it is called, and how far out it stands."""

    def __init__(self, name, miles):
        self.name = name
        self.miles = miles

    def __repr__(self):
        return f"House({self.name!r}, {self.miles!r})"


class Delivery:
    """One drop: the house, the month, the kind of coal, how many sacks went
    in, and how many empty sacks were handed back at the door."""

    def __init__(self, house, month, grade, sacks, empties=0):
        self.house = house
        self.month = month
        self.grade = grade
        self.sacks = sacks
        self.empties = empties

    def __repr__(self):
        return (
            f"Delivery({self.house!r}, {self.month!r}, {self.grade!r}, "
            f"{self.sacks!r}, {self.empties!r})"
        )


class Round:
    """A season of drops, in the order they were written down."""

    def __init__(self, deliveries):
        self.deliveries = list(deliveries)

    def at(self, house, month):
        """What this house had in this month, in the order written down."""
        return [
            delivery
            for delivery in self.deliveries
            if delivery.house.name == house.name and delivery.month == month
        ]

    def months(self, house):
        """Every month this house had anything, first written down first."""
        months = []
        for delivery in self.deliveries:
            if delivery.house.name == house.name and delivery.month not in months:
                months.append(delivery.month)
        return months
