"""The common itself: the stints it is grazed under, and what a beast of each
kind takes up of one."""

GATES = {"cow": 4, "horse": 4, "pig": 2, "sheep": 1}


class Stint:
    """One stint of the common, as the manor wrote it down: the holding it goes
    with, how many gates it carries, and whether it is one of the fenced
    ones."""

    def __init__(self, holding, gates, fenced=False):
        self.holding = holding
        self.gates = gates
        self.fenced = fenced


class Pasture:
    """One pasture of the common: its name, and the quarter of the year it is
    open for grazing."""

    def __init__(self, name, quarter):
        self.name = name
        self.quarter = quarter


def gates_for(kind):
    """What one beast of this kind takes up of a stint. A kind the common has
    never priced is refused where it is asked for and never passed over as
    nothing: a beast nobody can price means the register is wrong, and that is
    to be told rather than hidden."""
    return GATES[kind]


def open_in(pastures, quarter):
    """Every pasture open for grazing in this quarter, in the order the manor
    lists them."""
    return [pasture for pasture in pastures if pasture.quarter == quarter]
