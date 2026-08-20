"""The author's reference suite for the signal box's train register.

The task's registered existence proof: the suite a perfect agent would have
written, at the shape the prompt asks for — `test_*.py` under `tests/`,
standing on its own, no conftest.py and no helper module beside it. The lint
runs it against the pristine repository and against each planted behaviour
change in turn, which is what says the task is solvable exactly as written.

Never overlaid into a workdir, never collected by a verdict: it lives here,
beside repo/, where every action's existence proof lives.
"""

import pytest

from register import MOVEMENTS, read_entry, work_the_register


def entry(clock="09:15", headcode="1A24", movement="accepted"):
    return f"{clock} {headcode} {movement}"


def worked(*lines):
    return work_the_register(list(lines))


# --- one line of the register --------------------------------------------------


def test_a_line_is_read_into_the_three_things_it_records():
    assert read_entry("09:15 1A24 accepted") == {
        "minute": 555,
        "headcode": "1A24",
        "movement": "accepted",
    }


def test_midnight_is_nought_and_the_last_minute_of_the_day_is_the_last():
    assert read_entry(entry(clock="00:00"))["minute"] == 0
    assert read_entry(entry(clock="23:59"))["minute"] == 1439


def test_the_fields_are_parted_by_whatever_whitespace_stands_between_them():
    read = read_entry("   09:15\t\t1A24   accepted  ")

    assert read == {"minute": 555, "headcode": "1A24", "movement": "accepted"}


def test_a_line_that_is_not_three_fields_is_an_error():
    with pytest.raises(ValueError):
        read_entry("09:15 1A24")
    with pytest.raises(ValueError):
        read_entry("09:15 1A24 accepted twice")
    with pytest.raises(ValueError):
        read_entry("")


def test_a_clock_reading_of_the_wrong_shape_is_an_error():
    for clock in ("9:15", "09-15", "0915", "ab:cd", "09:1"):
        with pytest.raises(ValueError):
            read_entry(entry(clock=clock))


def test_an_hour_the_clock_does_not_reach_is_an_error():
    with pytest.raises(ValueError):
        read_entry(entry(clock="24:00"))
    with pytest.raises(ValueError):
        read_entry(entry(clock="99:15"))


def test_a_minute_the_clock_does_not_reach_is_an_error():
    with pytest.raises(ValueError):
        read_entry(entry(clock="09:60"))


def test_a_headcode_is_a_digit_a_capital_and_two_digits():
    assert read_entry(entry(headcode="1A24"))["headcode"] == "1A24"
    assert read_entry(entry(headcode="9Z00"))["headcode"] == "9Z00"


def test_a_headcode_written_in_a_small_letter_is_an_error():
    with pytest.raises(ValueError):
        read_entry(entry(headcode="1a24"))


def test_a_headcode_of_the_wrong_shape_is_an_error():
    for headcode in ("1A2", "1A245", "AA24", "1A2X", "1-24"):
        with pytest.raises(ValueError):
            read_entry(entry(headcode=headcode))


def test_the_three_movements_are_the_only_three():
    for movement in MOVEMENTS:
        assert read_entry(entry(movement=movement))["movement"] == movement
    for movement in ("Accepted", "left", "cleared."):
        with pytest.raises(ValueError):
            read_entry(entry(movement=movement))


# --- the register worked down --------------------------------------------------


def test_an_empty_register_holds_nothing_and_counts_nothing():
    assert worked() == {"in_section": None, "cleared": [], "movements": 0}


def test_a_train_offered_taken_and_given_back_leaves_the_section_free():
    assert worked(
        "09:15 1A24 accepted",
        "09:17 1A24 entered",
        "09:24 1A24 cleared",
    ) == {"in_section": None, "cleared": ["1A24"], "movements": 3}


def test_a_train_still_in_the_section_is_what_the_section_holds():
    assert worked("09:15 1A24 accepted", "09:17 1A24 entered") == {
        "in_section": "1A24",
        "cleared": [],
        "movements": 2,
    }


def test_the_section_is_free_again_the_moment_a_train_clears_it():
    section = worked(
        "09:15 1A24 accepted",
        "09:17 1A24 entered",
        "09:24 1A24 cleared",
        "09:30 2B10 accepted",
        "09:31 2B10 entered",
    )

    assert section["in_section"] == "2B10"
    assert section["cleared"] == ["1A24"]


def test_the_trains_that_cleared_are_given_back_in_the_order_they_cleared():
    section = worked(
        "09:15 1A24 accepted",
        "09:17 1A24 entered",
        "09:24 1A24 cleared",
        "09:30 2B10 accepted",
        "09:31 2B10 entered",
        "09:38 2B10 cleared",
    )

    assert section["cleared"] == ["1A24", "2B10"]
    assert section["movements"] == 6


def test_a_blank_line_is_spacing_and_is_not_a_movement():
    section = worked(
        "09:15 1A24 accepted",
        "",
        "   ",
        "09:17 1A24 entered",
    )

    assert section == {"in_section": "1A24", "cleared": [], "movements": 2}


def test_two_entries_at_the_same_minute_are_kept_in_order():
    section = worked(
        "09:15 1A24 accepted",
        "09:15 1A24 entered",
        "09:15 1A24 cleared",
    )

    assert section == {"in_section": None, "cleared": ["1A24"], "movements": 3}


def test_an_entry_earlier_than_the_one_above_it_is_an_error():
    with pytest.raises(ValueError):
        worked("09:15 1A24 accepted", "09:14 1A24 entered")


def test_a_second_train_cannot_take_a_section_that_is_held():
    with pytest.raises(ValueError):
        worked(
            "09:15 1A24 accepted",
            "09:16 2B10 accepted",
            "09:17 1A24 entered",
            "09:18 2B10 entered",
        )


def test_a_train_that_was_never_accepted_cannot_enter_the_section():
    with pytest.raises(ValueError):
        worked("09:17 1A24 entered")


def test_a_train_cannot_clear_a_section_it_is_not_in():
    with pytest.raises(ValueError):
        worked("09:24 1A24 cleared")
    with pytest.raises(ValueError):
        worked(
            "09:15 1A24 accepted",
            "09:17 1A24 entered",
            "09:24 2B10 cleared",
        )


def test_a_train_already_on_the_register_cannot_be_offered_again():
    with pytest.raises(ValueError):
        worked("09:15 1A24 accepted", "09:16 1A24 accepted")
    with pytest.raises(ValueError):
        worked(
            "09:15 1A24 accepted",
            "09:17 1A24 entered",
            "09:18 1A24 accepted",
        )


def test_a_train_that_cleared_can_be_offered_again_later_in_the_day():
    section = worked(
        "09:15 1A24 accepted",
        "09:17 1A24 entered",
        "09:24 1A24 cleared",
        "17:05 1A24 accepted",
        "17:07 1A24 entered",
    )

    assert section["in_section"] == "1A24"
    assert section["cleared"] == ["1A24"]


def test_a_line_the_book_cannot_read_stops_the_register():
    with pytest.raises(ValueError):
        worked("09:15 1A24 accepted", "09:17 1A24 shunted")
