"""The existence proof of the planted finding ('diary.py', 'Diary.cancel').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a hirer who takes their bookings out of the diary takes
out every one of them. The change walks the diary's own list while taking
entries out of it, so the walk steps over the entry that moved up into the
place of the one just removed: of two bookings standing together, the second
stays in the diary.
"""

from diary import Booking, Diary


def test_a_hirer_who_cancels_has_every_booking_taken_out():
    diary = Diary()
    diary.take(Booking("ada", "big", "friday", 6, 3))
    diary.take(Booking("ada", "small", "saturday", 6, 2))
    diary.take(Booking("bob", "big", "sunday", 6, 1))

    assert diary.cancel("ada") == 2
    assert [booking.who for booking in diary.bookings] == ["bob"]
