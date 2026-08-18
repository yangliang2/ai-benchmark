"""The apiary itself: the hives the club's bees stand in, and where in the yard
each of them stands."""

STANDS = ("the orchard", "the paddock", "the top field")

POUNDS_TO_A_JAR = 2


class Hive:
    """One hive standing in the yard: the mark it carries, the stand it sits
    on, and how many frames it was made up with."""

    def __init__(self, mark, stand, frames):
        self.mark = mark
        self.stand = stand
        self.frames = frames


class Yard:
    """The ground the hives stand on: whose it is, and how many stands were
    laid out on it."""

    def __init__(self, whose, stands):
        self.whose = whose
        self.stands = stands


def on_the_stand(hives, stand):
    """The hives sitting on this stand, in the order they were made up."""
    return [hive for hive in hives if hive.stand == stand]


def stands_in_use(hives):
    """How many stands these hives are sitting on. Two of them on the one stand
    are on the one stand, and it is counted once."""
    return len({hive.stand for hive in hives})


def standing(hives, mark):
    """The hive of this mark standing in the yard, or None where none of that
    mark stands in it. A mark is matched however it was written down, on the
    side it is asked for and on the side it was carried."""
    wanted = mark.strip().lower()
    for hive in hives:
        if hive.mark.strip().lower() == wanted:
            return hive
    return None


def jars(pounds):
    """How many jars a crop of this many pounds fills. A crop is put up in
    whole jars: what will not fill one is left in the tank until next time."""
    return pounds // POUNDS_TO_A_JAR
