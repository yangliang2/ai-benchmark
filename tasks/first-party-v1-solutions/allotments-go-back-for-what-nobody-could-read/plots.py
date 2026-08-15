"""The plots the society lets, and how a plot is written down.

A plot is a number and whoever holds it. Some plots have a standpipe on them
and some do not: the ones that do are gone round and read, and the ones that
do not are never read at all — which is not the same thing as being read and
found not to have moved.
"""

NOBODY = None

NO_STANDPIPE = False


class NotAPlot(ValueError):
    """What was written down where a plot number should be is not one."""


class Plot:
    """One plot on the site."""

    def __init__(self, number, holder=NOBODY, standpipe=NO_STANDPIPE):
        self.number = number
        self.holder = holder
        self.standpipe = standpipe

    def __repr__(self):
        return (
            f"Plot({self.number!r}, holder={self.holder!r}, "
            f"standpipe={self.standpipe!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, Plot):
            return NotImplemented
        return (self.number, self.holder, self.standpipe) == (
            other.number,
            other.holder,
            other.standpipe,
        )

    def __hash__(self):
        return hash((self.number, self.holder, self.standpipe))


def number_of(written):
    """The plot number something was written up against.

    The site's books have always had a plot as a bare number and the reader
    writes it that way; a hash in front of it is let through because half the
    site puts one there. Anything else is not a plot number, and saying so
    rather than picking one is the whole of this function's job — what nobody
    can make out is not plot nought.
    """
    try:
        return int(written.strip().lstrip("#"))
    except ValueError:
        raise NotAPlot(written) from None


def watered(plots):
    """The plots with a standpipe on them, lowest number first."""
    return sorted(
        (plot for plot in plots if plot.standpipe), key=lambda plot: plot.number
    )


def held_by(plots, holder):
    """The plots one person holds, in the order the site has them."""
    return [plot for plot in plots if plot.holder == holder]
