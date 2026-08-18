"""The roll of the club: who keeps bees here, and which hives are theirs."""


class Keeper:
    """One member of the club: who they are, and the marks of the hives they
    keep."""

    def __init__(self, who, hives):
        self.who = who
        self.hives = hives


class Roll:
    """The roll of the club, in the order its members joined."""

    def __init__(self):
        self.keepers = []

    def join(self, keeper):
        """Put a member on the roll. The roll holds them in the order they
        joined and puts one on as they are given: two of one name is for the
        secretary to sort out and not the roll's to refuse."""
        self.keepers.append(keeper)

    def member(self, who):
        """The member of this name, or None where the roll holds nobody of it.
        A name is matched however it was written down."""
        wanted = who.strip().lower()
        for keeper in self.keepers:
            if keeper.who.strip().lower() == wanted:
                return keeper
        return None

    def keeping(self, mark):
        """Everyone on the roll who keeps the hive of this mark, in the order
        they joined: a hive kept between two members is kept by both of
        them."""
        return [keeper for keeper in self.keepers if mark in keeper.hives]

    def hives_kept(self):
        """How many hives the club keeps between them: a hive kept between two
        members is still the one hive, and stands under the club to be counted
        once."""
        return len({mark for keeper in self.keepers for mark in keeper.hives})
