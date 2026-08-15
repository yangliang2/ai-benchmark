"""The society: the plots it lets, what it has written against them, and what
it makes of a run of cards.

What comes off the site is cards; what goes up on the wall is the sheet. The
two are not the same thing, and the difference between them is the plots
nobody could make out: those are left off the sheet and go on the list to go
back to, and the reader takes a fresh card round to them.
"""

from cards import Unreadable, written_up
from ledger import NOTHING_USED
from plots import watered

NO_NOTE = ""


class Society:
    """The site, its plots, and the notes the society keeps against them."""

    def __init__(self, plots, notes=None):
        self.plots = list(plots)
        self.notes = dict(notes or {})

    def standpipes(self):
        """The plots the reader goes round, lowest number first."""
        return watered(self.plots)

    def note_on(self, plot):
        """Whatever the society has written against one plot, and nothing
        where it has written nothing."""
        try:
            return self.notes[plot]
        except KeyError:
            return NO_NOTE

    def read(self, quarter):
        """What one run came to: the figures that could be made out, and the
        plots to go back to.

        A plot whose card could not be made out is left out of the figures
        altogether and goes on the list: it is gone back to with a fresh card,
        and until that one comes in the society has no figure for it.
        """
        figures = {}
        going_back = []
        for plot in quarter.carded():
            try:
                figures[plot] = quarter.used_on(plot)
            except Unreadable:
                going_back.append(plot)
        return figures, going_back

    def sheet(self, quarter):
        """The sheet that goes up on the wall: every plot that could be made
        out, and what it got through."""
        return self.read(quarter)[0]

    def to_go_back_to(self, quarter):
        """The plots whose card nobody could make out."""
        return self.read(quarter)[1]

    def altogether(self, quarter):
        """What the whole site got through on one run."""
        got_through = NOTHING_USED
        for units in self.sheet(quarter).values():
            got_through += units
        return got_through

    def book(self, quarter):
        """The book for one run: every card written up as it came back."""
        return [written_up(quarter.card_for(plot)) for plot in quarter.carded()]
