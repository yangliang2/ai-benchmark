"""The register of the common: who holds a stint on it, and what they have
turned out on it."""


class Grazier:
    """One commoner with a stint on the common: who they are, and how many
    gates the stint carries."""

    def __init__(self, who, gates):
        self.who = who
        self.gates = gates


class Beast:
    """One beast turned out on the common: whose it is, what kind it is, and
    the mark it was branded with."""

    def __init__(self, who, kind, mark):
        self.who = who
        self.kind = kind
        self.mark = mark


class Register:
    """Who holds a stint on the common, in the order the stints were taken
    up, and what has been turned out on them."""

    def __init__(self):
        self.graziers = []
        self.beasts = {}

    def hold(self, grazier):
        """Take a commoner's stint up. The register holds them in the order
        they were taken up."""
        self.graziers.append(grazier)

    def holder(self, who):
        """The commoner of this name, or None where no commoner of that name
        holds a stint."""
        for grazier in self.graziers:
            if grazier.who == who:
                return grazier
        return None

    def enter(self, beast):
        """Write down a beast turned out on the common. Whether the stint
        carries it is no business of the register's: the reeve writes down
        what was turned out, and overstocking is for the court."""
        self.beasts.setdefault(beast.who, []).append(beast)

    def turned_out(self, who):
        """What this commoner has turned out, in the order it was written
        down. What the register hands out is a copy: a beast is turned out by
        writing it in the register and in no other way."""
        return list(self.beasts.get(who, []))
