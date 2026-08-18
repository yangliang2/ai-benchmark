"""The band: who rings in this tower, and which bell each of them stands at."""


class Ringer:
    """One ringer of the band: who they are, and the bell they usually stand
    at."""

    def __init__(self, who, bell):
        self.who = who
        self.bell = bell


class Band:
    """The band of the tower, in the order its ringers were taken on."""

    def __init__(self):
        self.ringers = []

    def take_on(self, ringer):
        """Take a ringer on. The band holds them in the order they were taken
        on and takes them as they are given: two of one name is for the captain
        to sort out and not the band's to refuse."""
        self.ringers.append(ringer)

    def standing_at(self, bell):
        """Everyone of the band who usually stands at this bell, in the order
        they were taken on."""
        return [each for each in self.ringers if each.bell == bell]

    def ringer(self, who):
        """The ringer of this name, or None where the band holds nobody of it.
        A name is matched however it was written down: the book is kept by
        whoever is holding the pencil, so the spaces around a name and the
        capitals in it are no part of it."""
        wanted = who.strip().lower()
        for each in self.ringers:
            if each.who.strip().lower() == wanted:
                return each
        return None
