"""The fare table: what a crossing of each class costs, as it stands."""

from ledger import Book


def set_fare(book: Book, kind: str, pence: int) -> None:
    """The board's price for a class of crossing, set or changed.

    One figure a class: setting a fare replaces whatever figure stood
    before, and the table carries no more than what every class costs now.
    """
    if pence < 1:
        raise ValueError("a fare is at least a penny")
    book["fares"][kind] = pence


def fare_for(book: Book, kind: str) -> int:
    """What a crossing of this class costs, off the table as it stands."""
    if kind not in book["fares"]:
        raise KeyError(f"no fare is set for a {kind!r} crossing")
    fare: int = book["fares"][kind]
    return fare
