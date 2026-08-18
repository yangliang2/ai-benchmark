"""The tower itself: the bells hung in it, and the clock the ringing is timed
by."""

BELLS = ("treble", "second", "third", "fourth", "fifth", "tenor")


class Bell:
    """One bell hung in the tower: the name it hangs under, and what it weighs
    in hundredweight."""

    def __init__(self, called, hundredweight):
        self.called = called
        self.hundredweight = hundredweight


class Frame:
    """The frame the bells hang in: the tower it stands in, and how many pits
    it was built with."""

    def __init__(self, where, pits):
        self.where = where
        self.pits = pits


def minutes(pulled_off, came_round):
    """How long a peal stood, in minutes of the tower clock: from the stroke it
    was pulled off at to the stroke it came round at, both of them read off the
    clock as minutes since midnight."""
    return came_round - pulled_off


def heaviest_first(bells):
    """The bells in the order they are rung down, the heaviest at the head of
    it: ordered by what a bell weighs and never by the way the weight is
    written."""
    return sorted(bells, key=lambda bell: bell.hundredweight, reverse=True)


def hung(bells, called):
    """The bell of this name hanging in the frame, or None where the frame
    holds none of that name. A name is matched however it was written down, on
    the side it is asked for and on the side it was hung."""
    wanted = called.strip().lower()
    for bell in bells:
        if bell.called.strip().lower() == wanted:
            return bell
    return None
