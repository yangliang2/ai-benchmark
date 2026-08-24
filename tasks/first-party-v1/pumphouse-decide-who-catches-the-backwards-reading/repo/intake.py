"""Every way the pump-house's book changes.

Each function takes the loaded book and changes it in place; saving is the
caller's job (cli.py loads once, applies one change, saves once). Days are
ISO date strings, "1927-03-25", so they compare and sort as text.
"""

from typing import Any

from ledger import Book


def _house(book: Book, name: str) -> dict[str, Any]:
    if name not in book["houses"]:
        raise KeyError(f"no house called {name!r} is metered in the book")
    entry: dict[str, Any] = book["houses"][name]
    return entry


def last_reading(book: Book, name: str) -> dict[str, Any] | None:
    """The newest reading line a house has, or None before its first visit.

    A house's readings are refused out of day order below, so its newest
    line is the last of its lines in entry order.
    """
    lines = [line for line in book["readings"] if line["house"] == name]
    return lines[-1] if lines else None


def fit(book: Book, day: str, name: str) -> None:
    """Take a house onto the book: a meter fitted where none was before."""
    if name in book["houses"]:
        raise ValueError(f"{name!r} is already metered in the book")
    book["houses"][name] = {"fitted": day}


def refit(book: Book, day: str, name: str) -> None:
    """A worn or stuck meter taken off the wall and a fresh one screwed on.

    The fresh dial starts at nought, so the first reading after a refit
    stands lower than the last one before it: the drop is the fitting, not
    the water. The house's line keeps the day of its newest fitting; the
    readings stay as the reader called them.
    """
    entry = _house(book, name)
    entry["fitted"] = day


def read_meter(book: Book, day: str, name: str, dial: int, note: str = "") -> None:
    """The reader's visit: the dial as it stands, onto the book.

    The book refuses what the one line shows to be wrong on its own — a
    house it does not know, a dial below nought, a visit dated before the
    house's last. What the dial reads is taken as the reader calls it.
    """
    _house(book, name)
    if dial < 0:
        raise ValueError("a dial cannot read below nought")
    last = last_reading(book, name)
    if last is not None and day < last["day"]:
        raise ValueError(
            f"{name!r} was last read on {last['day']} and a visit cannot be "
            "entered before it — readings arrive in day order"
        )
    book["readings"].append({"day": day, "house": name, "dial": dial, "note": note})
