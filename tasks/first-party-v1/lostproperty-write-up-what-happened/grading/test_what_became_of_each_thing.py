"""Held out: what a thing that will not keep is settled with, and written up as."""

from handins import Handin, ticket_for
from office import Office, wording
from sorting import AUCTION, BINNED, RETURNED, SHELF, Desk, outstayed

TODAY = 200

# Two that will not keep: one in today, one in since the spring. Under the
# defect the first is settled to the shelf and the second to the sale room —
# the two halves of one fall-through.
SANDWICHES = Handin("sandwiches", 200, keeps=False)
FLOWERS = Handin("flowers", 10, keeps=False)
# One that will not keep and has been asked for, which goes back either way.
CAKE = Handin("cake", 150, keeps=False, claimed=True)
# Three that keep, one for each of the other verdicts.
UMBRELLA = Handin("umbrella", 199)
COAT = Handin("coat", 40)
KEYS = Handin("keys", 190, claimed=True)


def test_what_will_not_keep_is_thrown_out_the_evening_it_comes_in():
    assert Desk().verdict(SANDWICHES, TODAY) == BINNED


def test_what_will_not_keep_is_thrown_out_however_long_it_has_been_in():
    assert Desk().verdict(FLOWERS, TODAY) == BINNED


def test_what_will_not_keep_still_goes_in_the_bin_beside_the_desk():
    desk = Desk()
    desk.verdict(FLOWERS, TODAY)
    desk.verdict(SANDWICHES, TODAY)
    assert desk.thrown == [FLOWERS, SANDWICHES]


def test_something_asked_for_goes_back_even_when_it_will_not_keep():
    desk = Desk()
    assert desk.verdict(CAKE, TODAY) == RETURNED
    assert desk.thrown == []


def test_the_verdicts_on_what_keeps_are_what_they_were():
    desk = Desk()
    assert desk.verdict(KEYS, TODAY) == RETURNED
    assert desk.verdict(COAT, TODAY) == AUCTION
    assert desk.verdict(UMBRELLA, TODAY) == SHELF
    assert desk.thrown == []


def test_the_evening_puts_what_will_not_keep_in_the_binned_pile():
    piles = Desk().evening([UMBRELLA, SANDWICHES, FLOWERS, COAT, KEYS], TODAY)

    assert piles.binned == (FLOWERS, SANDWICHES)
    assert piles.returned == (KEYS,)
    assert piles.sold == (COAT,)
    assert piles.shelved == (UMBRELLA,)
    assert len(piles.everything()) == 5


def test_the_book_says_what_became_of_each_thing():
    office = Office([UMBRELLA, SANDWICHES, FLOWERS, KEYS])

    assert office.written_up(TODAY) == [
        "keys: back to its owner",
        "flowers: thrown out",
        "sandwiches: thrown out",
        "umbrella: on the shelf",
    ]


def test_nothing_that_will_not_keep_is_written_up_as_kept():
    office = Office([UMBRELLA, SANDWICHES, FLOWERS, COAT, KEYS])

    assert office.counted(TODAY) == {
        RETURNED: 1,
        BINNED: 2,
        AUCTION: 1,
        SHELF: 1,
    }


def test_the_desk_still_keeps_things_for_as_long_as_it_is_told_to():
    assert Desk(keeping=30).verdict(UMBRELLA, TODAY) == SHELF
    assert Desk(keeping=0).verdict(UMBRELLA, TODAY) == AUCTION
    assert Desk(keeping=0).verdict(SANDWICHES, TODAY) == BINNED


def test_the_neighbouring_reckonings_are_unchanged():
    """What the fix must leave alone: what is still the office's in the
    morning, how long a thing has been here, the ticket tied to it, and the
    words a verdict is written up in."""
    desk = Desk()
    assert not desk.held_over(SANDWICHES, TODAY)
    assert not desk.held_over(FLOWERS, TODAY)
    assert desk.held_over(UMBRELLA, TODAY)
    assert outstayed(FLOWERS, TODAY)
    assert not outstayed(SANDWICHES, TODAY)
    assert ticket_for(SANDWICHES, TODAY) == "sandwiches - see the desk"
    assert wording(BINNED) == "thrown out"
    assert wording(AUCTION) == "sent to the sale room"
