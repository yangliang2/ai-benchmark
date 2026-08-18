"""The reeve's year: the days the manor court is held, and what the reeve has
kept of them."""

COURT_DAYS = ("Hock Monday", "Midsummer", "Michaelmas", "Martinmas")


class Reeve:
    """The reeve of the year: who they are, and the court days they have kept
    so far."""

    def __init__(self, who):
        self.who = who
        self.kept = []

    def keep(self, day):
        """Write down a court day the reeve has kept."""
        self.kept.append(day)

    def days_kept(self):
        """The court days this reeve has kept, in the order they were written
        down — a copy of them, so that the one way into what the reeve has kept
        is to write a day down here."""
        return list(self.kept)


def still_to_keep(reeve):
    """The court days of the year this reeve has still to keep, in the order
    the manor holds them."""
    return [day for day in COURT_DAYS if day not in reeve.kept]


def shared_out(pence, over):
    """`pence` shared between `over` of them, the way the parish shares
    anything that will not divide evenly: the odd pence go to the first, so
    the shares always come to what was shared out."""
    if over <= 0:
        return []
    shares = [pence // over] * over
    shares[0] += pence - sum(shares)
    return shares
