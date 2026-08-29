"""The tape: how the exchange keeps the day's calls, and what a look costs."""


class Tape:
    """The day's calls on one ticker tape, and the tally of windings.

    Each call cried from the rostrum is punched onto the tape in order.
    Reading a call back means winding the tape until that punch sits under
    the glass, so the house has always tallied windings: every one
    stretches the paper and wears the sprockets, and a tape wound too
    often tears before the day is settled. The tally is the house's own
    record, kept here for the same reason the till keeps a roll; nothing
    about it is for a test's benefit.
    """

    def __init__(self, calls):
        self._calls = list(calls)
        self.windings = 0

    def length(self):
        """How many calls the day has punched so far."""
        return len(self._calls)

    def call_at(self, place):
        """The call punched at this place: (hour cried, price cried)."""
        self.windings += 1
        return self._calls[place]
