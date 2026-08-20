"""The signal box's train register.

One line of the register read on its own, and the whole register worked down
in the order it was kept.
"""

# What the register records a train doing, and the only three words for it.
MOVEMENTS = ("accepted", "entered", "cleared")


def read_entry(line):
    """One line of the register, read into a mapping.

    `{"minute": minutes past midnight, "headcode": ..., "movement": ...}`.
    """
    fields = line.split()
    if len(fields) != 3:
        raise ValueError(f"a register line is three fields: {line!r}")
    clock, headcode, movement = fields
    return {
        "minute": _minute(clock),
        "headcode": _headcode(headcode),
        "movement": _movement(movement),
    }


def work_the_register(lines):
    """The register worked down from the top, as the box would work it.

    Gives back what the section holds now, the headcodes that cleared it in
    the order they cleared, and how many entries were read.
    """
    section = {"in_section": None, "cleared": [], "movements": 0}
    offered = set()
    kept_at = None
    for line in lines:
        if not line.strip():
            # A blank line is the box's own spacing, not a movement.
            continue
        entry = read_entry(line)
        if kept_at is not None and entry["minute"] < kept_at:
            raise ValueError("the register is kept in the order things happened")
        kept_at = entry["minute"]
        _record(section, offered, entry)
        section["movements"] += 1
    return section


def _record(section, offered, entry):
    headcode = entry["headcode"]
    movement = entry["movement"]
    if movement == "accepted":
        if headcode in offered or headcode == section["in_section"]:
            raise ValueError(f"{headcode} is on the register already")
        offered.add(headcode)
    elif movement == "entered":
        if headcode not in offered:
            raise ValueError(f"{headcode} entered the section unaccepted")
        if section["in_section"] is not None:
            raise ValueError("the section holds one train at a time")
        offered.discard(headcode)
        section["in_section"] = headcode
    else:
        if section["in_section"] != headcode:
            raise ValueError(f"{headcode} cleared a section it was not in")
        section["in_section"] = None
        section["cleared"].append(headcode)


def _minute(clock):
    if len(clock) != 5 or clock[2] != ":":
        raise ValueError(f"not a time of day: {clock!r}")
    hours, minutes = clock[:2], clock[3:]
    if not hours.isdigit() or not minutes.isdigit():
        raise ValueError(f"not a time of day: {clock!r}")
    if int(hours) > 23:
        raise ValueError(f"no such hour: {clock!r}")
    if int(minutes) > 59:
        raise ValueError(f"no such minute: {clock!r}")
    return int(hours) * 60 + int(minutes)


def _headcode(headcode):
    if len(headcode) != 4:
        raise ValueError(f"not a headcode: {headcode!r}")
    if not headcode[0].isdigit() or not headcode[2:].isdigit():
        raise ValueError(f"not a headcode: {headcode!r}")
    if not ("A" <= headcode[1] <= "Z"):
        raise ValueError(f"not a headcode: {headcode!r}")
    return headcode


def _movement(movement):
    if movement not in MOVEMENTS:
        raise ValueError(f"no such movement: {movement!r}")
    return movement
