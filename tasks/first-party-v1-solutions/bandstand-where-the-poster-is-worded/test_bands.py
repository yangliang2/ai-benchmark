from bands import Band, billed_as


def test_a_band_with_no_singer_keeps_its_name():
    assert billed_as(Band("The Ferrymen", 8)) == "The Ferrymen"


def test_a_singer_is_named_after_the_band():
    assert billed_as(Band("The Ferrymen", 8, "Iris Vane")) == "The Ferrymen with Iris Vane"


def test_a_band_of_one_keeps_its_name_however_it_is_entered():
    assert billed_as(Band("Kenneth Pomeroy", 1, "Kenneth Pomeroy")) == "Kenneth Pomeroy"
