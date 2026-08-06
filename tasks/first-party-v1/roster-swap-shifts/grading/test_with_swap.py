"""How `with_swap` is graded: by what happens to the roster it was *given*.

The near half — the roster that comes back has the right person on the right
day, in the right place — is what a reader of the change checks, and a swap
built on `dict(roster)` answers it perfectly: the mapping is new, so the
returned roster reads exactly as it should. What that shallow copy shares is
every day's list of people, and nothing says so until somebody looks at the
old roster again or puts somebody on a shift of either one. That is a
different call, usually in a different part of the program, which is what
makes this the far half.

Expected values are written out here rather than read back through the
module, so a rewritten `who_is_on` or `describe` cannot make a wrong answer
look right.
"""

import pytest
from roster import add_shift, new_roster, who_is_on, with_swap

WEEK = ["mon", "tue", "wed"]


def staffed():
    """The roster every test starts from, built the way the module builds one."""
    roster = new_roster(WEEK)
    for day, people in (("mon", ["ana", "ben", "cal"]), ("tue", ["dee"])):
        for name in people:
            add_shift(roster, day, name)
    return roster


def as_written(roster):
    """Who is on each day, read straight off the roster's own mapping."""
    return {day: list(people) for day, people in roster.items()}


BEFORE = {"mon": ["ana", "ben", "cal"], "tue": ["dee"], "wed": []}


# --- the near half: the roster that comes back ---------------------------------


def test_the_arriving_person_takes_the_leaving_ones_place_in_the_order():
    swapped = with_swap(staffed(), "mon", "ben", "eli")

    assert who_is_on(swapped, "mon") == ["ana", "eli", "cal"]


def test_every_other_day_comes_back_exactly_as_it_was():
    swapped = with_swap(staffed(), "mon", "ben", "eli")

    assert as_written(swapped) == {
        "mon": ["ana", "eli", "cal"],
        "tue": ["dee"],
        "wed": [],
    }


def test_the_days_keep_their_order():
    swapped = with_swap(staffed(), "tue", "dee", "eli")

    assert list(swapped) == WEEK


def test_swapping_the_only_person_on_a_shift_leaves_one_person_on_it():
    swapped = with_swap(staffed(), "tue", "dee", "eli")

    assert who_is_on(swapped, "tue") == ["eli"]


# --- the far half: the roster it was given, and the two afterwards --------------


def test_the_roster_it_was_given_is_left_exactly_as_it_was():
    roster = staffed()

    with_swap(roster, "mon", "ben", "eli")

    assert as_written(roster) == BEFORE


def test_putting_someone_on_the_swapped_day_of_one_does_not_touch_the_other():
    roster = staffed()

    swapped = with_swap(roster, "mon", "ben", "eli")
    add_shift(swapped, "mon", "fay")

    assert as_written(roster) == BEFORE


def test_putting_someone_on_an_untouched_day_of_one_does_not_touch_the_other():
    roster = staffed()

    swapped = with_swap(roster, "mon", "ben", "eli")
    add_shift(swapped, "wed", "fay")

    assert as_written(roster) == BEFORE


def test_the_old_roster_can_still_be_changed_without_the_new_one_noticing():
    roster = staffed()

    swapped = with_swap(roster, "mon", "ben", "eli")
    add_shift(roster, "tue", "fay")

    assert as_written(swapped) == {
        "mon": ["ana", "eli", "cal"],
        "tue": ["dee"],
        "wed": [],
    }


def test_two_swaps_of_one_roster_do_not_reach_each_other():
    roster = staffed()

    first = with_swap(roster, "mon", "ana", "eli")
    second = with_swap(roster, "mon", "cal", "fay")

    assert who_is_on(first, "mon") == ["eli", "ben", "cal"]
    assert who_is_on(second, "mon") == ["ana", "ben", "fay"]
    assert as_written(roster) == BEFORE


# --- what a swap refuses -------------------------------------------------------


def test_swapping_out_someone_who_is_not_on_that_shift_is_refused():
    roster = staffed()

    with pytest.raises(ValueError):
        with_swap(roster, "tue", "ana", "eli")

    assert as_written(roster) == BEFORE


def test_swapping_in_someone_already_on_that_shift_is_refused():
    roster = staffed()

    with pytest.raises(ValueError):
        with_swap(roster, "mon", "ben", "cal")

    assert as_written(roster) == BEFORE


def test_an_unknown_day_has_no_shift_to_swap():
    with pytest.raises(KeyError):
        with_swap(staffed(), "sun", "ana", "eli")
