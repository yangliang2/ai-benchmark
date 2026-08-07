"""How `windows` is graded: against the strips of counts the prompt spells out.

Every decision is stated — which side of a boundary a photograph falls on,
which is the window that opens on its second and not the one that closes
there; a window nothing was taken in, which counts none and is still printed;
and where the strip starts and stops, which is the first photograph and the
last — so the expected strips are written out here in full. This is the
zero-crux control the picking task is read against.
"""

import pytest
from roll import Photo, windows

SHOOT = [
    Photo(0, "heron", ""),
    Photo(1, "heron again", ""),
    Photo(5, "reeds", ""),
    Photo(6, "reeds again", "blurred"),
    Photo(20, "sunset", "keep"),
]


def test_the_strip_counts_the_photos_window_by_window():
    assert windows(list(SHOOT), 5) == [2, 2, 0, 0, 1]


def test_a_photo_on_a_windows_opening_second_belongs_to_that_window():
    """The one at five seconds opens the second window rather than closing the
    first."""
    assert windows([Photo(0, "one", ""), Photo(5, "other", "")], 5) == [1, 1]


def test_a_window_nothing_was_taken_in_counts_none_and_is_still_printed():
    assert windows([Photo(0, "one", ""), Photo(9, "other", "")], 3) == [1, 0, 0, 1]


def test_the_windows_start_at_the_first_photo_rather_than_at_the_hour():
    assert windows([Photo(7, "lone", "")], 3) == [1]


def test_the_last_window_is_the_one_the_last_photo_falls_in():
    """A roll that runs out inside its first window is one window long, not
    two: there is no empty window printed after the last photograph."""
    assert windows([Photo(0, "one", ""), Photo(4, "other", "")], 5) == [2]


def test_photos_taken_in_the_same_second_are_counted_once_each():
    assert windows([Photo(2, "one", ""), Photo(2, "other", "")], 4) == [2]


def test_a_window_of_a_single_second_counts_a_photo_a_second():
    assert windows([Photo(0, "one", ""), Photo(1, "other", "")], 1) == [1, 1]


def test_an_empty_roll_gives_an_empty_strip():
    assert windows([], 5) == []


@pytest.mark.parametrize("every", [0, -1, -5])
def test_a_window_of_no_seconds_or_fewer_is_refused(every):
    with pytest.raises(ValueError):
        windows(list(SHOOT), every)


def test_a_roll_that_does_not_run_in_time_order_is_refused():
    with pytest.raises(ValueError):
        windows([Photo(9, "late", ""), Photo(1, "early", "")], 5)


def test_the_roll_the_caller_passed_in_is_left_alone():
    roll = list(SHOOT)

    windows(roll, 5)

    assert roll == list(SHOOT)
