"""The table of doles: what the almshouse gives out at the door.

Each kind of dole is what the trustees have settled it as, changed rarely;
the clerk has no discretion at the door. An unknown kind is refused rather
than guessed at, because a dole the table has no entry for is a dole the
trustees never granted.
"""

DOLES = {
    "bread": "a quartern loaf",
    "coal": "half a hundredweight",
    "shillings": "two shillings",
}


def dole(kind: str) -> str:
    """The table's entry for one kind of dole: what is actually handed over."""
    if kind not in DOLES:
        raise KeyError(f"no dole granted for {kind!r}")
    return DOLES[kind]


def kinds() -> list[str]:
    """Every kind the table grants, in name order."""
    return sorted(DOLES)
