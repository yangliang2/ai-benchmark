"""The mill itself: the pairs of stones it grinds with, and the water that
drives them."""

FLOORS = ("the bin floor", "the stone floor", "the meal floor")

PECKS_TO_A_BUSHEL = 4

PECKS_TO_A_SACK = 8


class Stones:
    """One pair of stones: the name they go by, the floor they stand on, and
    how many furrows they were last dressed with."""

    def __init__(self, name, floor, furrows):
        self.name = name
        self.floor = floor
        self.furrows = furrows


class Leat:
    """The water the mill is driven by: whose it is, and the fall it comes down
    with."""

    def __init__(self, whose, fall):
        self.whose = whose
        self.fall = fall


def on_the_floor(stones, floor):
    """The pairs of stones standing on this floor, in the order they were put
    in."""
    return [pair for pair in stones if pair.floor == floor]


def floors_in_use(stones):
    """How many floors these pairs of stones stand on. Two of them on the one
    floor are on the one floor, and it is counted once."""
    return len({pair.floor for pair in stones})


def turning(stones, name):
    """The pair of stones of this name, or None where none of that name stands
    in the mill. A name is matched however it was written down, on the side it
    is asked for and on the side it was given."""
    wanted = name.strip().lower()
    for pair in stones:
        if pair.name.strip().lower() == wanted:
            return pair
    return None


def bushels(pecks):
    """How many whole bushels a lot of this many pecks comes to. What will not
    fill a bushel is not a bushel, and is left out of the reckoning."""
    return pecks // PECKS_TO_A_BUSHEL


def sacks_to_carry(pecks):
    """How many sacks a lot of this many pecks takes to carry off. A lot part
    filling a sack still takes a sack to carry it: what will not fill one is
    carried in a sack of its own."""
    return -(-pecks // PECKS_TO_A_SACK)
