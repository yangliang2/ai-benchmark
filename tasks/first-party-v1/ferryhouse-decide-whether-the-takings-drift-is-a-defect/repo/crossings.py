"""Every crossing line the ferry-house's book takes on.

Each function takes the loaded book and changes it in place; saving is the
caller's job (cli.py loads once, applies one change, saves once). Days are
ISO date strings, "1929-04-11", so they compare and sort as text.
"""

from fares import fare_for
from ledger import Book


def cross(book: Book, day: str, kind: str, note: str = "") -> None:
    """A crossing made and paid at the box.

    The line is the crossing, not the money: it carries the day, the class
    and the note, and what the crossing cost is looked up off the fare
    table whenever the takings are counted. A class with no fare set is
    refused — the box cannot take money no figure names.
    """
    fare_for(book, kind)
    book["crossings"].append({"day": day, "kind": kind, "note": note})


def refund(book: Book, day: str, kind: str, note: str = "") -> None:
    """A crossing turned back: the fare goes back out of the box.

    The clerk hands back what the table says a crossing of that class
    costs, and the line records the turning-back the way a crossing is
    recorded — day, class and note, and no figure.
    """
    fare_for(book, kind)
    book["crossings"].append({"day": day, "kind": kind, "back": True, "note": note})
