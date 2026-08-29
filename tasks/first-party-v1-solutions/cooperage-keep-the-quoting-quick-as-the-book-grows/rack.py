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

        The day's order book, answered in the order it was taken. The rack
        is gauged in one round at the top — each cask once, in racked
        order — and every order in the book is answered off that gauging,
        so a long book costs no more rod-work than a short one.
        """
        gauged = sorted(
            (self._gauge.measure(cask), position, cask.name)
            for position, cask in enumerate(self._casks)
        )
        return [(gallons, self._snuggest(gauged, gallons)) for gallons in orders]

    @staticmethod
    def _snuggest(gauged, gallons):
        """The snuggest fit off an already-gauged rack: the first entry that
        holds the order, smallest capacity first and racked order within a
        capacity, which is cask_for's own rule."""
        for capacity, _, name in gauged:
            if capacity >= gallons:
                return name
        return None
