"""Where a hamper is packed: the standard hamper, and the bespoke ones.

The shop sells one standard hamper, and it is the same hamper for
everybody — what it holds is settled here and nowhere else. A bespoke
order brings its own list and is packed to that instead.
"""

from typing import Any

# What the standard hamper holds. Every standard order is packed to
# this list.
STANDARD = [
    "a quarter of tea",
    "a bag of sugar",
    "a fruit cake",
    "a jar of marmalade",
]


def make_up(customer: str, wants: list[str] | None = None) -> dict[str, Any]:
    """Make up one hamper.

    A bespoke order is packed to its own list; a standard order is
    packed to the standard one.
    """
    if wants is not None:
        contents = list(wants)
    else:
        contents = STANDARD
    return {"customer": customer, "contents": contents}


def add_extra(hamper: dict[str, Any], item: str) -> None:
    """Slip one more item into a made-up hamper."""
    hamper["contents"].append(item)
