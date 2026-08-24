"""What gets read back out of the ferry-house's book."""

from fares import fare_for
from ledger import Book


def takings_between(book: Book, start: str, end: str) -> int:
    """The box's money between two days, counted off the book, in pence.

    Every crossing line dated in [start, end], priced off the fare table as
    it stands, a turned-back crossing counted out of the box rather than in.
    """
    total = 0
    for line in book["crossings"]:
        if start <= line["day"] <= end:
            fare = fare_for(book, line["kind"])
            total += -fare if line.get("back") else fare
    return total


def tally_between(book: Book, start: str, end: str) -> str:
    """Crossings by class between two days: made and turned back, one line a
    class, in class order."""
    made: dict[str, int] = {}
    back: dict[str, int] = {}
    for line in book["crossings"]:
        if start <= line["day"] <= end:
            counted = back if line.get("back") else made
            counted[line["kind"]] = counted.get(line["kind"], 0) + 1
    lines = []
    for kind in sorted(set(made) | set(back)):
        lines.append(
            f"{kind}  {made.get(kind, 0)} crossed  {back.get(kind, 0)} turned back"
        )
    return "\n".join(lines)
