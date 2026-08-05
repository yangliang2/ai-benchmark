"""Standings for a small tournament ladder."""


class Player:
    """One competitor, the points they have taken and any bonus awarded."""

    def __init__(self, name, points, bonus=0):
        self.name = name
        self.points = points
        self.bonus = bonus

    def total(self):
        """Everything the player has scored."""
        return self.points + self.bonus

    def __repr__(self):
        return f"Player({self.name!r}, {self.points}, {self.bonus})"


def standings(players):
    """The players in ranking order, highest total first."""
    return sorted(players, key=lambda player: -player.total())


def top(players, count):
    """The first `count` players in ranking order."""
    return sorted(players, key=lambda player: -player.total())[:count]


def rank_of(players, name):
    """Where the player called `name` places, counting from 1."""
    ordered = sorted(players, key=lambda player: -player.total())
    for place, player in enumerate(ordered, start=1):
        if player.name == name:
            return place
    raise KeyError(f"no player called {name}")
