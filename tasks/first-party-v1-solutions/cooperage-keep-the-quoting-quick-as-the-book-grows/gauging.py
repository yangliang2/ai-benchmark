"""Gauging: how the cooperage learns what a cask actually holds."""


class Gauge:
    """The shop's gauging rod, and the tally of how often it is used.

    Gauging a cask means unbunging it, dropping the rod, and reading the
    wetted length against the scale, so the shop has always tallied
    gaugings: every one costs the cooper a walk to the rack and costs the
    cask a spell open to the air. The tally is the shop's own record, kept
    here for the same reason the till keeps a roll; nothing about it is for
    a test's benefit.
    """

    def __init__(self):
        self.gaugings = 0

    def measure(self, cask):
        """The cask's capacity in gallons, read off the rod.

        The cooper's rule of thumb: a cask holds near enough its mean
        girth squared times its height, scaled to gallons and floored to
        the whole gallon the shop quotes in.
        """
        self.gaugings += 1
        return (cask.girth * cask.girth * cask.height) // 1000
