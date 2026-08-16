from counter import Window
from office import Office
from parcels import Parcel

DAY = [
    Parcel("a keyring", 90, 12),
    Parcel("a paperback", 400, 20),
    Parcel("biscuits", 1200, 34),
]

NOTES = {"biscuits": "call in before Friday"}

# A light thing that will not go in the small sack whatever the scale says.
AWKWARD = [Parcel("a birdcage", 300, 40)]


def office():
    return Office(NOTES)


def window():
    return Window(DAY)


def test_a_note_written_against_a_parcel_comes_back_as_it_was_written():
    assert office().note_on("biscuits") == "call in before Friday"


def test_a_parcel_with_nothing_written_against_it_has_nothing_written():
    assert office().note_on("a keyring") == ""


def test_the_sack_a_parcel_leaves_in_is_the_one_the_gauge_puts_it_in():
    assert office().sack_for(window(), "a keyring") == "the pouch"
    assert office().sack_for(window(), "a paperback") == "the small sack"
    assert office().sack_for(window(), "biscuits") == "the big sack"


def test_a_light_awkward_parcel_still_goes_in_the_sack_it_will_fit_in():
    """The sacks are packed off the gauge and the scale has no say in it."""
    awkward = Window(AWKWARD)

    assert office().sack_for(awkward, "a birdcage") == "the big sack"
    assert office().two_to_carry(awkward, "a birdcage") is False


def test_it_takes_two_to_carry_out_what_the_scale_says_is_a_load():
    assert office().two_to_carry(window(), "biscuits") is True
    assert office().two_to_carry(window(), "a keyring") is False


def test_the_day_comes_to_what_was_charged_over_the_counter():
    assert office().takings(window()) == 740


def test_a_day_nobody_brought_anything_in_on_comes_to_nothing():
    assert office().takings(Window([])) == 0


def test_the_book_writes_up_every_parcel_the_day_took_in():
    assert office().book(window()) == [
        "a keyring: £1.65",
        "a paperback: £2.35",
        "biscuits: £3.40",
    ]
