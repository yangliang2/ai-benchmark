"""The coals themselves, and what a sack of each fetches in a given month.

Nothing in here counts sacks, knows which door they went to, or adds anything
to anything. It answers one narrow question: what a single sack of this kind
is worth in this month of the year, the cold half of the year being dearer
than the warm.
"""

# The months the yard calls cold, and charges for as such.
COLD = ("oct", "nov", "dec", "jan", "feb", "mar")

# Pence a sack costs above its warm-weather price in a cold month.
COLD_EXTRA = 14


class Grade:
    """One kind of coal: what it is called, and what a sack of it fetches in
    the warm half of the year."""

    def __init__(self, name, warm_pence):
        self.name = name
        self.warm_pence = warm_pence

    def __repr__(self):
        return f"Grade({self.name!r}, {self.warm_pence!r})"


def price_of(grade, month):
    """What one sack of this kind fetches in this month, in pence."""
    if month in COLD:
        return grade.warm_pence + COLD_EXTRA
    return grade.warm_pence
