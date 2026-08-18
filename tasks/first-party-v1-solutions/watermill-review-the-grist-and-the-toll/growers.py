"""The round: who brings corn to the mill, and the farms it comes off."""


class Grower:
    """One grower on the round: who they are, and the farm their corn comes
    off."""

    def __init__(self, who, farm):
        self.who = who
        self.farm = farm


class Round:
    """The mill's round, in the order its growers came on."""

    def __init__(self):
        self.growers = []

    def come_on(self, grower):
        """Put a grower on the round. The round holds them in the order they
        came on and puts one on as they are given: two of one name is for the
        miller to sort out and not the round's to refuse."""
        self.growers.append(grower)

    def grower(self, who):
        """The grower of this name, or None where the round holds nobody of it.
        A name is matched however it was written down."""
        wanted = who.strip().lower()
        for grower in self.growers:
            if grower.who.strip().lower() == wanted:
                return grower
        return None

    def farms(self):
        """Every farm the round's corn comes off, in the order they first came
        on: two growers off the one farm are off the one farm."""
        seen = []
        for grower in self.growers:
            if grower.farm not in seen:
                seen.append(grower.farm)
        return seen
