"""The rack of casks, and the day's quoting over it."""


class Cask:
    """One cask on the rack: its name, and the two measures gauging reads."""

    def __init__(self, name, girth, height):
        self.name = name
        self.girth = girth
        self.height = height


class Rack:
    """Every cask the shop holds, in the order they were racked, and the
    gauge the shop measures them with."""

    def __init__(self, casks, gauge):
        self._casks = list(casks)
        self._gauge = gauge

    def cask_for(self, gallons):
        """The name of the snuggest cask that holds this order.

        The snuggest fit is the smallest capacity at or above the order;
        between casks of equal capacity, the one racked first. None when no
        cask on the rack is big enough.
        """
        best = None
        best_capacity = None
        for cask in self._casks:
            capacity = self._gauge.measure(cask)
            if capacity < gallons:
                continue
            if best_capacity is None or capacity < best_capacity:
                best, best_capacity = cask.name, capacity
        return best

    def quote(self, orders):
        """One line per order: (gallons asked, name of the cask to draw).

        The day's order book, answered in the order it was taken.
        """
        return [(gallons, self.cask_for(gallons)) for gallons in orders]
