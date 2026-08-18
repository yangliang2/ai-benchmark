"""What a booking is charged: the hire of the room, and the price agreed."""

from hall import named

HEATING_PENCE = 250
WINTER_MONTHS = (11, 12, 1, 2, 3)


def to_the_pound(pence):
    """A charge as it goes on the bill: up to the whole pound."""
    return -(-pence // 100) * 100


def heating(month):
    """What the heating adds to an evening in this month."""
    return HEATING_PENCE if month in WINTER_MONTHS else 0


def hire_for(booking, rate):
    """The hire of a room for one booking: the rate for the hours booked,
    the heating on top of it in the winter months, and the whole of it up to
    the pound."""
    return to_the_pound(rate * booking.hours) + heating(booking.month)


def price_of(booking, rate):
    """What the hirer is charged for a booking: the price agreed for it
    where one was agreed, and the hire of the room where none was."""
    if booking.agreed:
        return booking.agreed
    return hire_for(booking, rate)


def takings(bookings, rooms):
    """What these bookings came to, in pence."""
    return sum(
        price_of(booking, named(rooms, booking.room).rate) for booking in bookings
    )
