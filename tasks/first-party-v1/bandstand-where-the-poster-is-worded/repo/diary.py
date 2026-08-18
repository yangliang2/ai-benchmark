"""What is booked, and for which afternoon.

The diary keeps dates and knows nothing about print: it will say what is
booked for an afternoon and in which order the turns come, and which
afternoons of the season have anything booked at all. It never puts two
things together into one phrase.
"""


class Booking:
    """One engagement: the date, the band, the hour it begins, and how many
    minutes it runs for."""

    def __init__(self, date, band, begins, minutes):
        self.date = date
        self.band = band
        self.begins = begins
        self.minutes = minutes

    def __repr__(self):
        return f"Booking({self.date!r}, {self.band!r}, {self.begins!r}, {self.minutes!r})"


class Diary:
    """A season's engagements, in no particular order until asked."""

    def __init__(self, bookings):
        self.bookings = list(bookings)

    def on(self, date):
        """What is booked for this afternoon, earliest first.

        Two turns beginning at the same hour keep the order they were entered
        in, which is the order the secretary took them down in.
        """
        booked = [booking for booking in self.bookings if booking.date == date]
        return sorted(booked, key=lambda booking: booking.begins)

    def dates(self):
        """Every afternoon of the season with anything booked, in date order."""
        return sorted({booking.date for booking in self.bookings})
