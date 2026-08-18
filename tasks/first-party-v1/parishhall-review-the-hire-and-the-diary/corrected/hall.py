"""The rooms of the parish hall, and what each of them will take."""


class Room:
    """One room of the hall, as the committee has it written down."""

    def __init__(self, name, seats, rate):
        self.name = name
        self.seats = seats
        self.rate = rate


def named(rooms, name):
    """The room of this name, or None where the hall has no such room."""
    for room in rooms:
        if room.name == name:
            return room
    return None


def big_enough(rooms, party):
    """Every room that will seat a party this size, in name order."""
    return sorted(room.name for room in rooms if room.seats >= party)
