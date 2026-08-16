"""Held out: what a parcel is charged when the scale and the gauge disagree.

Graded through what the office charges rather than through how it arrives at
it: the prompt reports one parcel charged a line further down the card than it
should have been and a day's takings over by the difference, so those are what
is asserted. Which reading the price is looked up against is the author's
business and not the fix's — what is asserted is that the money follows the
scale and the sacks still follow the gauge.
"""

import pytest
from card import NotOnTheCard, to_pay, written_as
from counter import Charge, Window, most_charged
from office import Office
from parcels import (
    Parcel,
    TooBig,
    size_band,
    taken_in,
    to_the_gauge,
    to_the_scale,
    weight_band,
)

NOTES = {"biscuits": "call in before Friday"}

# Tuesday, with the lampshade in it: next to no weight, and a great awkward
# thing round the middle. The scale puts it in band B and the gauge in band C.
DAY = [
    Parcel("a keyring", 90, 12),
    Parcel("a paperback", 400, 20),
    Parcel("a lampshade", 300, 40),
    Parcel("biscuits", 1200, 34),
]

# The same day with a parcel whose two readings agree in place of the
# lampshade, which is every ordinary day the office has.
ORDINARY = [
    Parcel("a keyring", 90, 12),
    Parcel("a paperback", 400, 20),
    Parcel("a jar of honey", 900, 22),
    Parcel("biscuits", 1200, 34),
]


def office():
    return Office(NOTES)


def test_a_parcel_is_charged_what_the_card_says_against_what_it_weighed():
    assert Window(DAY).postage_on("a lampshade") == 235


def test_an_awkward_parcel_is_charged_no_more_than_a_neat_one_of_its_weight():
    """The two are the same weight and nothing else about them is priced."""
    assert Window(DAY).postage_on("a lampshade") == Window(ORDINARY).postage_on(
        "a paperback"
    )


def test_the_day_comes_to_what_the_scale_said_and_not_a_penny_over():
    assert office().takings(Window(DAY)) == 975


def test_every_parcel_of_the_day_is_priced_off_the_scale():
    assert office().charges(Window(DAY)) == [
        Charge("a keyring", 165),
        Charge("a paperback", 235),
        Charge("a lampshade", 235),
        Charge("biscuits", 340),
    ]


def test_the_book_writes_up_what_was_paid():
    assert office().book(Window(DAY)) == [
        "a keyring: £1.65",
        "a paperback: £2.35",
        "a lampshade: £2.35",
        "biscuits: £3.40",
    ]


def test_an_ordinary_day_is_charged_exactly_as_it_always_was():
    """The other half of the same claim, and what makes it worth asserting: on
    a parcel whose two readings agree nothing whatever changes, which is why
    nobody noticed."""
    assert office().takings(Window(ORDINARY)) == 975
    assert office().charges(Window(ORDINARY)) == [
        Charge("a keyring", 165),
        Charge("a paperback", 235),
        Charge("a jar of honey", 235),
        Charge("biscuits", 340),
    ]


def test_a_day_of_nothing_but_awkward_parcels_is_priced_off_the_scale_too():
    lot = [
        Parcel("a birdcage", 300, 40),
        Parcel("a wreath", 200, 34),
        Parcel("a lampshade", 300, 40),
    ]

    assert office().takings(Window(lot)) == 235 + 165 + 235


def test_the_sacks_are_still_packed_off_the_gauge():
    """What the fix must leave alone. The lampshade went off in the right sack
    and got where it was going: it is the money that was wrong, and a repair
    that priced the parcel right by making the gauge say something else would
    have put it in the small sack it does not fit in."""
    window = Window(DAY)

    assert office().sack_for(window, "a lampshade") == "the big sack"
    assert office().sack_for(window, "a keyring") == "the pouch"
    assert office().sack_for(window, "a paperback") == "the small sack"
    assert office().sack_for(window, "biscuits") == "the big sack"


def test_who_carries_a_parcel_out_is_still_the_scales_business():
    window = Window(DAY)

    assert office().two_to_carry(window, "biscuits") is True
    assert office().two_to_carry(window, "a lampshade") is False


def test_the_neighbouring_reckonings_are_unchanged():
    """What the fix must leave alone: the two runs of bands and where their
    lines fall, the prices on the card, how money and a charge are written up,
    the order parcels are taken in, what the office has written against a
    label, and what happens to something that runs off the end of either
    reading."""
    window = Window(DAY)

    assert window.handed_in() == [
        "a keyring", "a paperback", "a lampshade", "biscuits",
    ]
    assert window.parcel_for("a lampshade") == Parcel("a lampshade", 300, 40)
    assert window.weighed("a lampshade") == "B"
    assert weight_band(90) == "A"
    assert weight_band(1000) == "B"
    assert weight_band(4000) == "C"
    assert size_band(12) == "A"
    assert size_band(40) == "C"
    assert to_pay("A") == 165
    assert to_pay("B") == 235
    assert to_pay("C") == 340
    assert to_pay("D") == 495
    assert written_as(340) == "£3.40"
    assert Charge("biscuits", 340).written_up() == "biscuits: £3.40"
    assert most_charged(office().charges(window)) == Charge("biscuits", 340)
    assert most_charged([]) is None
    assert taken_in(["a paperback, 400, 20"]) == [Parcel("a paperback", 400, 20)]
    assert to_the_scale(DAY, "B") == [
        Parcel("a paperback", 400, 20),
        Parcel("a lampshade", 300, 40),
    ]
    assert to_the_gauge(DAY, "C") == [
        Parcel("a lampshade", 300, 40),
        Parcel("biscuits", 1200, 34),
    ]
    assert office().note_on("biscuits") == "call in before Friday"
    assert office().note_on("a keyring") == ""

    with pytest.raises(TooBig):
        weight_band(40000)
    with pytest.raises(TooBig):
        size_band(96)
    with pytest.raises(NotOnTheCard):
        to_pay("E")
