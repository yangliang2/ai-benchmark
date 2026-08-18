"""The existence proof of the planted finding ('charges.py', 'price_of').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that where a price has been agreed with the committee that
is what the hirer is charged, and that an evening agreed at nothing is an
evening that costs nothing. The change asks whether the agreed price is true
rather than whether one was agreed at all, so the charity evening the
committee agreed at nothing is billed the hire of the room.
"""

from charges import price_of
from diary import Booking


def test_an_evening_agreed_at_nothing_is_an_evening_that_costs_nothing():
    booking = Booking("ada", "big", "friday", 6, 3, agreed=0)

    assert price_of(booking, 400) == 0
