from charges import heating, takings, to_the_pound
from diary import Booking
from hall import Room


def test_a_charge_goes_on_the_bill_at_the_pound_above_it():
    assert to_the_pound(1180) == 1200


def test_a_charge_of_whole_pounds_stays_where_it_is():
    assert to_the_pound(1200) == 1200


def test_the_heating_goes_on_an_evening_of_the_winter_months_only():
    assert heating(1) == 250
    assert heating(6) == 0


def test_what_a_summer_evening_of_three_hours_came_to():
    bookings = [Booking("ada", "big", "friday", 6, 3)]

    assert takings(bookings, [Room("big", 80, 400)]) == 1200
