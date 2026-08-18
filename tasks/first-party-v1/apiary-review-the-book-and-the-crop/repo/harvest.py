"""The harvest book: what has come off the hives of the club, and what the book
makes of it."""


class Take:
    """One lot as it came off: the mark of the hive it came off, the summer it
    was taken in, how many pounds it came to, and who took it off."""

    def __init__(self, mark, summer, pounds, who):
        self.mark = mark
        self.summer = summer
        self.pounds = pounds
        self.who = who


class Book:
    """The club's harvest book: the lots it holds, in the order they came
    off."""

    def __init__(self):
        self.takes = []
        self._worked_out = {}

    def take_off(self, take):
        """Set a lot down in the book as it came off. The book holds them in
        the order they were taken off."""
        self.takes.append(take)

    def off_hive(self, mark):
        """Each lot that came off the hive of this mark, in the order they were
        taken off."""
        return [take for take in self.takes if take.mark == mark]

    def taken_by(self, who, summer):
        """How many pounds this member took off in this summer. The sheet in
        the hut asks the book this once a member, so what the book has worked
        out once it keeps and hands back again."""
        if who in self._worked_out:
            return self._worked_out[who]
        pounds = sum(
            take.pounds
            for take in self.takes
            if take.who == who and take.summer == summer
        )
        self._worked_out[who] = pounds
        return pounds
