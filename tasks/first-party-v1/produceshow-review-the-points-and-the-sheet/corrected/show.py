"""The schedule of the show: the classes there are to enter, and the section
each of them is judged in."""


class Class:
    """One class of the schedule, as the committee has it written down: what
    is shown in it, the section it is judged in, and whether the championship
    rides on it."""

    def __init__(self, name, section, championship=False):
        self.name = name
        self.section = section
        self.championship = championship


class Section:
    """One section of the schedule: its name, and the tent it is judged in."""

    def __init__(self, name, tent):
        self.name = name
        self.tent = tent


def named(classes, name):
    """The class of this name, or None where the schedule has no such class."""
    for cls in classes:
        if cls.name == name:
            return cls
    return None


def under(classes, section):
    """Every class judged in this section, in the order the schedule lists
    them."""
    return [cls for cls in classes if cls.section == section]
