import pytest
from roster import (
    add_shift,
    days,
    describe,
    drop_shift,
    new_roster,
    who_is_on,
)

WEEK = ["mon", "tue", "wed"]


def staffed():
    roster = new_roster(WEEK)
    add_shift(roster, "mon", "ana")
    add_shift(roster, "mon", "ben")
    add_shift(roster, "tue", "cal")
    return roster


def test_a_new_roster_has_a_shift_a_day_and_nobody_on_any_of_them():
    roster = new_roster(WEEK)

    assert days(roster) == WEEK
    assert [who_is_on(roster, day) for day in WEEK] == [[], [], []]


def test_people_stay_in_the_order_they_were_put_on_a_shift():
    assert who_is_on(staffed(), "mon") == ["ana", "ben"]


def test_dropping_someone_leaves_the_others_in_their_order():
    roster = staffed()

    drop_shift(roster, "mon", "ana")

    assert who_is_on(roster, "mon") == ["ben"]


def test_the_same_person_cannot_be_put_on_one_shift_twice():
    roster = staffed()

    with pytest.raises(ValueError):
        add_shift(roster, "mon", "ana")


def test_dropping_someone_who_is_not_on_the_shift_is_refused():
    roster = staffed()

    with pytest.raises(ValueError):
        drop_shift(roster, "tue", "ana")


def test_an_unknown_day_is_not_a_shift():
    roster = staffed()

    with pytest.raises(KeyError):
        who_is_on(roster, "sun")


def test_the_shift_reader_hands_back_a_list_of_its_own():
    roster = staffed()

    who_is_on(roster, "mon").clear()

    assert who_is_on(roster, "mon") == ["ana", "ben"]


def test_the_description_names_the_empty_days_too():
    assert describe(staffed()) == [
        "mon: ana, ben",
        "tue: cal",
        "wed: (nobody)",
    ]
