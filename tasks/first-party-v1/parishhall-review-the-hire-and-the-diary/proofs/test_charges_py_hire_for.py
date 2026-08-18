"""The existence proof of the planted finding ('charges.py', 'hire_for').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a room is hired at the rate on the room for the hours
booked, that the heating goes on the bill as well from November to March, and
that what the hirer is asked for is the whole of that rounded up to the pound.
The change rounds the hire up to the pound first and adds the heating to the
rounded figure, so a winter evening is billed at a figure that is not a whole
pound at all.
"""

from charges import hire_for
from diary import Booking


def test_the_whole_of_a_winter_evening_is_rounded_up_to_the_pound():
    booking = Booking("ada", "big", "friday", 1, 3)

    assert hire_for(booking, 310) == 1200
