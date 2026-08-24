"""Every way the granary's book changes.

Each function takes the loaded book and changes it in place; saving is the
caller's job (cli.py loads once, applies one change, saves once). Days are
ISO date strings, "1926-03-25", so they compare and sort as text.
"""

from typing import Any

from ledger import Book


def _bin(book: Book, name: str) -> dict[str, Any]:
    if name not in book["bins"]:
        raise KeyError(f"no bin called {name!r} in the book")
    entry: dict[str, Any] = book["bins"][name]
    return entry


def open_bin(book: Book, day: str, name: str, grain: str, sacks: int) -> None:
    """Take a bin onto the book, counted as it stands.

    The starting count is the bin's own line, not a movement: nothing came
    through the door on the day the book took the bin on. The sacks were
    already sitting there, and the movement lines record the door.
    """
    if name in book["bins"]:
        raise ValueError(f"{name!r} is already on the book")
    if sacks < 0:
        raise ValueError("a bin cannot open with a negative count")
    book["bins"][name] = {"grain": grain, "sacks": sacks, "opened": day}


def take_in(book: Book, day: str, name: str, sacks: int, note: str = "") -> None:
    """A delivery: sacks in through the door, onto the bin's count."""
    if sacks < 1:
        raise ValueError("a delivery is at least one sack")
    entry = _bin(book, name)
    entry["sacks"] += sacks
    book["movements"].append(
        {"day": day, "bin": name, "kind": "in", "sacks": sacks, "note": note}
    )


def give_out(book: Book, day: str, name: str, sacks: int, note: str = "") -> None:
    """An issue: sacks out through the door. The book refuses an overdraw."""
    if sacks < 1:
        raise ValueError("an issue is at least one sack")
    entry = _bin(book, name)
    if sacks > entry["sacks"]:
        raise ValueError(
            f"{name!r} holds {entry['sacks']} sack(s) and cannot issue {sacks}"
        )
    entry["sacks"] -= sacks
    book["movements"].append(
        {"day": day, "bin": name, "kind": "out", "sacks": sacks, "note": note}
    )


def set_right(book: Book, day: str, name: str, counted: int) -> None:
    """The stocktake correction: the book is set to what the counting found.

    Spillage, sweepings, a delivery counted wrong at the door — a bin's count
    drifts, and at the annual stocktake every bin is counted and the book is
    made true. A correction is not grain through the door, so no movement is
    written: the bin's line is simply set to the counted figure, and the day
    it was last counted is kept on the line.
    """
    if counted < 0:
        raise ValueError("a count cannot come to a negative figure")
    entry = _bin(book, name)
    entry["sacks"] = counted
    entry["counted"] = day
