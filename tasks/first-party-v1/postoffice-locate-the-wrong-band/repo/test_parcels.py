import pytest
from parcels import (
    Parcel,
    TooBig,
    size_band,
    taken_in,
    to_the_gauge,
    to_the_scale,
    weight_band,
)

BROUGHT_IN = [
    Parcel("a keyring", 90, 12),
    Parcel("a paperback", 400, 20),
    Parcel("biscuits", 1200, 34),
]


def test_the_scale_puts_a_light_parcel_in_the_first_band():
    assert weight_band(90) == "A"


def test_the_scale_puts_a_heavier_parcel_further_down_the_run():
    assert weight_band(1200) == "C"


def test_a_parcel_right_on_a_line_goes_in_the_band_the_line_belongs_to():
    assert weight_band(1000) == "B"


def test_the_gauge_puts_a_neat_parcel_in_the_first_band():
    assert size_band(12) == "A"


def test_the_gauge_puts_an_awkward_parcel_further_down_the_run():
    assert size_band(40) == "C"


def test_a_light_parcel_can_be_an_awkward_one_all_the_same():
    """The two readings are taken separately, and an ordinary week brings in
    plenty of parcels the scale and the gauge put in different bands."""
    assert weight_band(300) == "B"
    assert size_band(40) == "C"


def test_a_heavy_parcel_can_be_a_neat_one_just_as_easily():
    assert weight_band(4000) == "C"
    assert size_band(16) == "A"


def test_what_runs_off_the_end_of_the_scale_does_not_go_through_here():
    with pytest.raises(TooBig):
        weight_band(40000)


def test_what_runs_off_the_end_of_the_gauge_does_not_go_through_here():
    with pytest.raises(TooBig):
        size_band(96)


def test_the_parcels_the_scale_puts_in_one_band_come_back_in_order():
    assert to_the_scale(BROUGHT_IN, "B") == [Parcel("a paperback", 400, 20)]


def test_the_parcels_the_gauge_puts_in_one_band_come_back_in_order():
    assert to_the_gauge(BROUGHT_IN, "C") == [Parcel("biscuits", 1200, 34)]


def test_the_two_readings_pick_out_different_parcels_of_a_day():
    """Nothing says the two runs of bands agree about a parcel, and on a day
    with an awkward one in it they do not."""
    day = [*BROUGHT_IN, Parcel("a birdcage", 300, 40)]

    assert [parcel.label for parcel in to_the_scale(day, "B")] == [
        "a paperback",
        "a birdcage",
    ]
    assert [parcel.label for parcel in to_the_gauge(day, "C")] == [
        "biscuits",
        "a birdcage",
    ]


def test_a_days_sheet_is_read_into_the_parcels_it_was_written_for():
    assert taken_in(["a paperback, 400, 20", "biscuits, 1200, 34"]) == [
        Parcel("a paperback", 400, 20),
        Parcel("biscuits", 1200, 34),
    ]
