"""The stewards of the show: who is on duty in which tent, and what is left of
their round."""

ROUND = ("setting out", "judging", "clearing away")

CLEARING_HOUR = 16


class Steward:
    """One steward: who they are, and the tent they are in."""

    def __init__(self, who, tent):
        self.who = who
        self.tent = tent


def in_tent(stewards, tent):
    """Every steward in this tent, in the order the duty list was made up. The
    list is in no tent order, so a steward of another tent is stepped over and
    is not an end of the walk."""
    found = []
    for steward in stewards:
        if steward.tent != tent:
            continue
        found.append(steward)
    return found


def left_of(steward, done=None):
    """What is left of a steward's round: the whole of it less what has been
    done, and the whole of it where nothing has been. What is handed in is
    read and never kept, so a round asked for twice with nothing handed in
    comes back whole both times."""
    already = () if done is None else done
    return [duty for duty in ROUND if duty not in already]


def duty_at(hour):
    """What the stewards are at in this hour of the day: once the tent is
    being cleared that is what everybody is at, whatever else the hour would
    have them doing. The narrower rule is asked first, or the broader one
    would answer for it."""
    if hour >= CLEARING_HOUR:
        return ROUND[-1]
    return ROUND[0] if hour < 10 else ROUND[1]
