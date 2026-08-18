"""The bookings: who has a room of the hall, when, and for how long."""


class Booking:
    """One booking: the hirer, the room, the day and month it falls in, and
    how many hours it runs to."""

    def __init__(self, who, room, day, month, hours, agreed=None):
        self.who = who
        self.room = room
        self.day = day
        self.month = month
        self.hours = hours
        self.agreed = agreed


class Diary:
    """Every booking of the season, in the order they were taken."""

    def __init__(self):
        self.bookings = []

    def take(self, booking):
        """Enter a booking in the diary."""
        self.bookings.append(booking)

    def on(self, day):
        """Every booking of this day, in the order they were taken."""
        return [booking for booking in self.bookings if booking.day == day]

    def cancel(self, who):
        """Take every booking of this hirer out of the diary; how many of
        them went."""
        gone = 0
        for booking in list(self.bookings):
            if booking.who == who:
                self.bookings.remove(booking)
                gone += 1
        return gone
