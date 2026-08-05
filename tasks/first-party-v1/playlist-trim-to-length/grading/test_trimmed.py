"""How `trimmed` is graded: against the prefix the prompt spells out.

Every decision is stated — where to stop, what to do with the track that would
overrun, what counts as an error — so the expected queues are written out in
full here. This is the zero-crux control the spacing task is compared against.
"""

import pytest
from playlist import Track, trimmed

QUEUE = [
    Track("dawn", "ora", 210),
    Track("dusk", "vek", 180),
    Track("noon", "ora", 240),
    Track("late", "kip", 40),
]


def test_a_queue_that_fits_is_kept_whole():
    assert trimmed(QUEUE, 670) == QUEUE


def test_the_track_that_would_overrun_ends_the_queue():
    assert trimmed(QUEUE, 500) == QUEUE[:2]


def test_a_track_that_fills_the_time_exactly_is_kept():
    assert trimmed(QUEUE, 390) == QUEUE[:2]


def test_a_later_track_is_not_reached_for_once_one_has_overrun():
    """The rule that separates a prefix from a knapsack: `late` would fit in
    what is left of the slot after dawn, and may not be picked up, because
    dusk has already ended the queue."""
    assert trimmed(QUEUE, 250) == QUEUE[:1]


def test_no_time_at_all_keeps_nothing():
    assert list(trimmed(QUEUE, 0)) == []


def test_an_empty_queue_stays_empty():
    assert list(trimmed([], 600)) == []


@pytest.mark.parametrize("seconds", [-1, -600])
def test_a_negative_length_is_refused(seconds):
    with pytest.raises(ValueError):
        trimmed(QUEUE, seconds)
