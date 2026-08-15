"""The addresses a walk goes past.

A house is one address: its number, the street it stands in, and the title it
takes, or nothing at all where it takes no paper. Streets are written in lower
case throughout, because that is how the shop's books have always had them and
two spellings of one street would be two streets.
"""

NO_PAPER = None


class House:
    """One address a walk goes past."""

    def __init__(self, number, street, takes=NO_PAPER):
        self.number = number
        self.street = street
        self.takes = takes

    def __repr__(self):
        return f"House({self.number!r}, {self.street!r}, takes={self.takes!r})"

    def __eq__(self, other):
        if not isinstance(other, House):
            return NotImplemented
        return (self.number, self.street, self.takes) == (
            other.number,
            other.street,
            other.takes,
        )

    def __hash__(self):
        return hash((self.number, self.street, self.takes))


def address(house):
    """The address a house is written down by."""
    return f"{house.number} {house.street}"


def in_order(houses, streets=[]):
    """The houses in the order a walk takes them: street by street, and up the
    numbers within a street.

    `streets` is the order the shop has written down for the streets it has
    written one down for, and a street it does not name comes after those in
    alphabetical order. It is read here and never added to — which street
    comes before which is the shop's to say, and not this function's to learn.
    """

    def walked(house):
        if house.street in streets:
            return (streets.index(house.street), "", house.number)
        return (len(streets), house.street, house.number)

    return sorted(houses, key=walked)


def taking(houses, title):
    """The houses that take one title, in the order they were given."""
    return [house for house in houses if house.takes == title]
