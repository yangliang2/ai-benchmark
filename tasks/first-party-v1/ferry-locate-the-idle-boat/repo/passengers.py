"""The people on the jetty, and the order they are taken in."""

PATIENCE = 20


class Passenger:
    """One person on the jetty: their name, and the minute they came down."""

    def __init__(self, name, came_down_at):
        self.name = name
        self.came_down_at = came_down_at

    def __repr__(self):
        return f"Passenger({self.name!r}, {self.came_down_at!r})"

    def __eq__(self, other):
        if not isinstance(other, Passenger):
            return NotImplemented
        return (self.name, self.came_down_at) == (other.name, other.came_down_at)

    def __hash__(self):
        return hash((self.name, self.came_down_at))


def in_turn(passengers):
    """The passengers in the order they are taken, earliest down first.

    Two who came down on the same minute keep the order they were given in,
    which is the order they reached the bottom of the steps.
    """
    return sorted(passengers, key=lambda passenger: passenger.came_down_at)


def waited_at_least(passenger, now, minutes=PATIENCE):
    """Whether this passenger has been on the jetty for `minutes` or more."""
    return now - passenger.came_down_at >= minutes
