"""The afternoons the doors are open, and whose turn it is at the desk."""

OPEN_DAYS = ("tuesday", "saturday")
DESK_OPENS_HOUR = 14
DESK_CLOSES_HOUR = 17


def is_open(day):
    """Whether the doors are open on this day, however the day is written
    down: a day is one of the two the shed opens on, or it is not."""
    return day.strip().lower() in OPEN_DAYS


def whose_turn(volunteers, week):
    """Whose turn it is at the desk in this week of the rota."""
    return volunteers[week % len(volunteers)]
