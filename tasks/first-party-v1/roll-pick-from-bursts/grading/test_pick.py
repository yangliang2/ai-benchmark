"""How `pick` is graded: by what a set of picks has to be, not by one set.

Which photograph of a burst survives is the decision the prompt deliberately
leaves open — several sets of picks satisfy the rules for the same roll and
the same pause, and every one of them is a correct answer — so what is checked
is that one photo came back from each burst and that it was one of that
burst's own, that a photo marked to keep is the one kept, and that a soft
frame is kept only where the whole burst was soft.

Every yardstick here is a literal written out beside the roll it belongs to:
each case says which photographs make up each burst, by their place on the
roll. A solution that came with a rewritten notion of where one burst ends and
the next begins would otherwise be graded against its own reading of the gaps.
"""

from typing import NamedTuple

import pytest
from roll import Photo, pick


class Case(NamedTuple):
    """One roll, the pause it is cut at, and the bursts it falls into —
    written out by hand as the places on the roll each burst holds."""

    roll: list
    pause: int
    bursts: list


CASES = {
    # One long burst and one photo on its own well after it.
    "settle": Case(
        roll=[
            Photo(0, "heron-a", ""),
            Photo(1, "heron-b", ""),
            Photo(2, "heron-c", ""),
            Photo(40, "reeds", ""),
        ],
        pause=2,
        bursts=[[0, 1, 2], [3]],
    ),
    # The first frame of the burst came out soft, so keeping the first frame
    # of every burst keeps a photo the rules rule out.
    "soft-start": Case(
        roll=[
            Photo(0, "gull-a", "blurred"),
            Photo(1, "gull-b", ""),
            Photo(2, "gull-c", ""),
            Photo(30, "sky", ""),
        ],
        pause=2,
        bursts=[[0, 1, 2], [3]],
    ),
    # Nothing in the burst came out: one of the soft frames has to stand for
    # it, because no burst may be passed over.
    "all-soft": Case(
        roll=[Photo(0, "mist-a", "blurred"), Photo(1, "mist-b", "blurred")],
        pause=2,
        bursts=[[0, 1]],
    ),
    # The photographer marked the frame they wanted, and it is not the first.
    "marked": Case(
        roll=[
            Photo(0, "deer-a", ""),
            Photo(1, "deer-b", "keep"),
            Photo(2, "deer-c", ""),
        ],
        pause=2,
        bursts=[[0, 1, 2]],
    ),
    # A gap of exactly the pause holds a burst together; a longer one does
    # not.
    "boundary": Case(
        roll=[Photo(0, "oak", ""), Photo(2, "elm", ""), Photo(5, "ash", "")],
        pause=2,
        bursts=[[0, 1], [2]],
    ),
    # Two photographs taken in the same second are always one burst.
    "same-second": Case(
        roll=[Photo(4, "twin-a", ""), Photo(4, "twin-b", ""), Photo(9, "lone", "")],
        pause=2,
        bursts=[[0, 1], [2]],
    ),
    # Every photo far enough from the next to stand alone.
    "apart": Case(
        roll=[Photo(0, "dawn", ""), Photo(10, "noon", "blurred"), Photo(20, "dusk", "")],
        pause=2,
        bursts=[[0], [1], [2]],
    ),
}

NAMES = sorted(CASES)


def given(name):
    """One roll, handed over as a list of its own, so that a solution which
    sorts or consumes what it was given fails the one rule about that and not
    the ones about something else."""
    return list(CASES[name].roll)


def picked(name):
    """What came back, as the places on the roll the picks were taken from.

    Found by identity rather than by value: two frames of one burst can agree
    in every field, and `list.index` would report both as the earlier one —
    which would read a pick of the second as a pick of the first. A frame that
    is on no roll at all reports -1, which fails the rule about that.
    """
    case = CASES[name]
    return [
        next((place for place, on_roll in enumerate(case.roll) if on_roll is photo), -1)
        for photo in pick(given(name), case.pause)
    ]


@pytest.mark.parametrize("name", NAMES)
def test_one_photo_comes_back_from_each_burst_and_it_is_one_of_that_bursts(name):
    places = picked(name)
    bursts = CASES[name].bursts

    assert len(places) == len(bursts)
    for place, burst in zip(places, bursts):
        assert place in burst


@pytest.mark.parametrize("name", NAMES)
def test_the_picks_come_back_in_the_order_they_were_taken(name):
    places = picked(name)

    assert places == sorted(places)


@pytest.mark.parametrize("name", NAMES)
def test_a_photo_marked_to_keep_is_the_one_kept_from_its_burst(name):
    case = CASES[name]
    places = picked(name)

    for place, burst in zip(places, case.bursts):
        wanted = [held for held in burst if case.roll[held].mark == "keep"]
        if wanted:
            assert [place] == wanted


@pytest.mark.parametrize("name", NAMES)
def test_a_soft_frame_is_kept_only_where_the_whole_burst_was_soft(name):
    """The rule that rules out keeping the first frame of every burst and
    calling the choice made."""
    case = CASES[name]
    places = picked(name)

    for place, burst in zip(places, case.bursts):
        if case.roll[place].mark == "blurred":
            assert all(case.roll[held].mark == "blurred" for held in burst)


@pytest.mark.parametrize("name", NAMES)
def test_the_roll_the_caller_passed_in_is_left_alone(name):
    roll = given(name)

    pick(roll, CASES[name].pause)

    assert roll == CASES[name].roll


def test_an_empty_roll_gives_no_picks():
    assert list(pick([], 2)) == []


def test_a_roll_that_does_not_run_in_time_order_is_refused():
    with pytest.raises(ValueError):
        pick([Photo(9, "late", ""), Photo(1, "early", "")], 2)


def test_a_burst_holding_two_photos_marked_to_keep_is_refused():
    with pytest.raises(ValueError):
        pick([Photo(0, "one", "keep"), Photo(1, "other", "keep")], 2)
