"""What gets read back out of the granary's book."""

from typing import Any

from ledger import Book


def stocktake(book: Book) -> str:
    """Every bin as it stands today, one line each, in name order."""
    lines = []
    for name in sorted(book["bins"]):
        entry = book["bins"][name]
        lines.append(f"{name}  {entry['grain']}  {entry['sacks']} sack(s)")
    return "\n".join(lines)


def held_by_grain(book: Book) -> dict[str, int]:
    """Today's holdings summed by grain, across every bin."""
    totals: dict[str, int] = {}
    for entry in book["bins"].values():
        totals[entry["grain"]] = totals.get(entry["grain"], 0) + entry["sacks"]
    return totals


def movements_between(book: Book, start: str, end: str) -> list[dict[str, Any]]:
    """The movement lines dated in [start, end], oldest first.

    Lines are kept in entry order; days compare as ISO date strings.
    """
    picked = [line for line in book["movements"] if start <= line["day"] <= end]
    return sorted(picked, key=lambda line: line["day"])
