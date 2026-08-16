from counter import Charge, Window, most_charged
from parcels import Parcel

DAY = [
    Parcel("a keyring", 90, 12),
    Parcel("a paperback", 400, 20),
    Parcel("biscuits", 1200, 34),
]


def window():
    return Window(DAY)


def test_a_day_knows_what_was_handed_in_and_in_what_order():
    assert window().handed_in() == ["a keyring", "a paperback", "biscuits"]


def test_the_parcel_taken_in_under_a_label_is_the_one_written_down_for_it():
    assert window().parcel_for("a paperback") == Parcel("a paperback", 400, 20)


def test_what_the_scale_made_of_a_parcel_is_the_band_it_goes_in():
    assert window().weighed("a keyring") == "A"
    assert window().weighed("a paperback") == "B"
    assert window().weighed("biscuits") == "C"


def test_what_a_parcel_costs_to_send_is_the_price_on_the_card():
    assert window().postage_on("a keyring") == 165
    assert window().postage_on("a paperback") == 235
    assert window().postage_on("biscuits") == 340


def test_a_parcel_priced_up_is_the_label_it_came_in_under_and_the_money():
    assert window().charge_for("a paperback") == Charge("a paperback", 235)


def test_a_charge_goes_down_in_the_book_as_the_label_and_the_money():
    assert Charge("biscuits", 340).written_up() == "biscuits: £3.40"


def test_the_dearest_parcel_of_a_day_is_the_one_that_cost_the_most():
    charges = [Charge("a keyring", 165), Charge("biscuits", 340)]

    assert most_charged(charges) == Charge("biscuits", 340)


def test_a_day_that_took_nothing_in_has_no_dearest_parcel():
    assert most_charged([]) is None
