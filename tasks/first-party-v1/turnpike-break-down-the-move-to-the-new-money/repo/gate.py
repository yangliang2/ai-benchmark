"""How a crossing goes onto the roll.

Each function takes the loaded roll and changes it in place; saving is the
caller's job (cli.py loads once, takes one crossing down, saves once). Days
are ISO date strings, "1926-03-25", so they compare and sort as text.
"""

import tariff
from roll import Roll


def cross(roll: Roll, day: str, kind: str, note: str = "") -> None:
    """One crossing taken at the gate, charged and written down.

    The charge is reckoned at the gate and written into the line: the roll
    says what was actually taken on the day, whatever the table is later
    changed to say.
    """
    charge = tariff.rate(kind)
    roll["lines"].append(
        {"day": day, "kind": kind, "charge": charge, "note": note}
    )


def wave_through(roll: Roll, day: str, kind: str, note: str) -> None:
    """A crossing let past without payment: the parson, the doctor, the mail.

    Still a crossing and still written down — the parish counts heads as well
    as pence — with a charge of nothing, and the note must say why.
    """
    if not note:
        raise ValueError("a crossing waved through needs its reason noted")
    tariff.rate(kind)  # an unknown kind is refused here as at the gate proper
    roll["lines"].append({"day": day, "kind": kind, "charge": 0, "note": note})
