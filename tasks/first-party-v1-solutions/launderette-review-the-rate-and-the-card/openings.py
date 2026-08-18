"""When the doors are open, and when a wash may still go on."""

OPEN_FROM_HOUR = 7
LAST_WASH_HOUR = 21
CLOSE_HOUR = 23


def is_open(hour):
    """Whether the doors are open at this hour."""
    return OPEN_FROM_HOUR <= hour < CLOSE_HOUR


def too_late_to_start(hour):
    """Whether it is past the hour the room takes its last load: nothing new
    goes on from nine at night onwards, so the floor is clear by closing."""
    return hour >= LAST_WASH_HOUR
