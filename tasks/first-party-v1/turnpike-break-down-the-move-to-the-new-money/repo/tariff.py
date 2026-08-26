"""The table of tolls: what each kind of crossing pays at the gate.

Rates are whole pence a crossing, set by the parish and changed rarely; the
keeper has no discretion at the gate. An unknown kind is refused rather than
guessed at, because a crossing the table has no rate for is a crossing the
parish never priced.
"""

RATES = {"cart": 5, "horse": 2, "foot": 1}


def rate(kind: str) -> int:
    """The table's rate for one kind of crossing, in pence."""
    if kind not in RATES:
        raise KeyError(f"no toll set for {kind!r}")
    return RATES[kind]


def kinds() -> list[str]:
    """Every kind the table prices, in name order."""
    return sorted(RATES)
