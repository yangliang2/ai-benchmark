"""What gets read back out of the pump-house's book."""

from ledger import Book


def stand(book: Book) -> str:
    """Every house as it stands: its newest dial, one line each, in name
    order, or a dash for a house not yet read."""
    lines = []
    for name in sorted(book["houses"]):
        newest = [line for line in book["readings"] if line["house"] == name]
        dial = str(newest[-1]["dial"]) if newest else "-"
        lines.append(f"{name}  {dial}")
    return "\n".join(lines)


def usage_between(book: Book, name: str, start: str, end: str) -> int:
    """Water through a house's meter between two days, summed off the dial.

    Usage is the difference between consecutive dial readings — each line's
    dial less the line before it — counted into the total when the later
    line's day falls in [start, end]. The figure is whatever the subtraction
    gives.
    """
    lines = [line for line in book["readings"] if line["house"] == name]
    total = 0
    for earlier, later in zip(lines, lines[1:]):
        if start <= later["day"] <= end:
            total += later["dial"] - earlier["dial"]
    return total


def bill(book: Book, name: str, start: str, end: str, pence_per_unit: int) -> int:
    """The quarter's bill in pence: the house's usage at the board's rate."""
    return usage_between(book, name, start, end) * pence_per_unit
