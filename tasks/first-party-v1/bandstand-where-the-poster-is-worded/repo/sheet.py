"""The printed sheet: what stands under each date, and how a season divides.

The diary supplies engagements and `bands.billed_as` supplies one band's own
name. Neither of them ever makes a phrase out of what it holds; that happens
in this module and nowhere else.
"""

from bands import billed_as

# A turn of this many minutes is unremarkable, and its length goes unsaid.
USUAL_MINUTES = 45

# What stands under a date nobody has taken.
QUIET = "nothing arranged"


class Column:
    """One column of the sheet: a heading, and the phrases beneath it."""

    def __init__(self, heading, phrases):
        self.heading = heading
        self.phrases = phrases

    def depth(self):
        """How many lines deep this column sets."""
        return len(self.phrases)

    def __repr__(self):
        return f"Column({self.heading!r}, {self.phrases!r})"


class Sheet:
    """A season's sheet, taken off one diary."""

    def __init__(self, diary):
        self.diary = diary

    def wording(self, date):
        """The phrase that stands under one date."""
        booked = self.diary.on(date)
        if not booked:
            return QUIET
        return ", then ".join(
            self._one(booking) for booking in booked
        )

    def _one(self, booking):
        phrase = f"{booking.begins} {billed_as(booking.band)}"
        if booking.minutes != USUAL_MINUTES:
            phrase += f" ({booking.minutes} minutes)"
        return phrase

    def columns(self, deepest):
        """A season's dates divided into columns no deeper than this."""
        dates = self.diary.dates()
        return [
            Column(dates[start], [self.wording(date) for date in dates[start:start + deepest]])
            for start in range(0, len(dates), deepest)
        ]
