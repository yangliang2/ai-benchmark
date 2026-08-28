"""The dispatch book: every coil that left the yard, tagged and priced."""

from typing import Any

from stores import Yard

# What a fathom of finished rope fetches, in pence, by lay.
PENCE_PER_FATHOM = {"hawser": 9, "shroud": 14}


def take_serial(yard: Yard) -> int:
    """The next tag number, taken off the book and stepped by one."""
    serial: int = yard["next_serial"]
    yard["next_serial"] = serial + 1
    return serial


def enter(yard: Yard, customer: str, asked: int, coil: dict[str, Any]) -> str:
    """Put a finished coil on the book. Returns the tag on the coil.

    The entry keeps both figures, the asking and the walk, and the price
    is taken over the coil's own length: every fathom on the tag was laid,
    and the book charges for what was walked.
    """
    tag = f"RW-{take_serial(yard)}"
    yard["dispatches"].append(
        {
            "tag": tag,
            "customer": customer,
            "asked": asked,
            "walked": coil["fathoms"],
            "lay": coil["lay"],
            "price_pence": coil["fathoms"] * PENCE_PER_FATHOM[coil["lay"]],
        }
    )
    return tag
