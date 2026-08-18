"""The entry book of the show: who has entered what, and how it was judged."""


class Entry:
    """One entry: the exhibitor, the class it is in, the number it was given
    on the day, and the placing the judge gave it."""

    def __init__(self, who, cls, number, place=None):
        self.who = who
        self.cls = cls
        self.number = number
        self.place = place


class Book:
    """Every entry taken, in the order they were taken."""

    def __init__(self):
        self.entries = []

    def take(self, entry):
        """Enter an exhibitor in a class; an exhibitor may be entered in one
        class as often as they like."""
        self.entries.append(entry)

    def of(self, who):
        """Every entry of this exhibitor, in the order they were taken."""
        return [entry for entry in self.entries if entry.who == who]

    def of_class(self, name):
        """The sheet for a class: every entry standing in it, in the order
        they were taken."""
        sheet = []
        for entry in self.entries:
            if entry.cls != name:
                continue
            sheet.append(entry)
        return sheet

    def judged(self, entry, place):
        """Mark the judge's placing on an entry. A class judged a second time
        is judged afresh, so the later placing stands over the earlier one."""
        entry.place = place
