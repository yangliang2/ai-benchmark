from diary import Booking, Diary


def taken():
    diary = Diary()
    diary.take(Booking("ada", "big", "friday", 6, 3))
    diary.take(Booking("bob", "small", "saturday", 6, 2))
    return diary


def test_a_booking_goes_in_the_diary_in_the_order_it_was_taken():
    assert [booking.who for booking in taken().bookings] == ["ada", "bob"]


def test_a_day_shows_the_bookings_of_that_day_and_no_others():
    assert [booking.room for booking in taken().on("friday")] == ["big"]
