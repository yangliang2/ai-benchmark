"""How `spread` is graded: by what a listenable queue is, not by one queue.

Which order to return is the decision the prompt deliberately leaves open —
several orders space the same tracks out and every one of them is a correct
answer — so what is checked is that the queue holds the right tracks, that no
artist is heard twice in a row, and that the one case where no such order
exists is refused rather than approximated.
"""

from collections import Counter

import pytest
from playlist import Track, spread


def queue(*artists):
    """Tracks by the artists named, each with a title of its own."""
    return [
        Track(f"t{position}", artist, 200)
        for position, artist in enumerate(artists)
    ]


QUEUES = {
    "alternating": queue("ora", "ora", "vek", "vek"),
    # ora holds three of the five: the most an artist can hold and still fit.
    "at-the-limit": queue("ora", "vek", "ora", "kip", "ora"),
    "long-tail": queue("ora", "ora", "ora", "vek", "vek", "kip", "raz"),
    "single": queue("ora"),
    "pair": queue("ora", "vek"),
    "empty": [],
}

NAMES = sorted(QUEUES)


def given(name):
    """One set of tracks, handed over as a copy of its own, so that a
    solution which works through the sequence it was given and consumes it
    fails the one test that rule has and not the ones about something else."""
    return list(QUEUES[name])


@pytest.mark.parametrize("name", NAMES)
def test_the_queue_holds_exactly_the_tracks_it_was_given(name):
    assert Counter(spread(given(name))) == Counter(QUEUES[name])


@pytest.mark.parametrize("name", NAMES)
def test_no_artist_is_heard_twice_in_a_row(name):
    played = list(spread(given(name)))

    for earlier, later in zip(played, played[1:]):
        assert earlier.artist != later.artist


@pytest.mark.parametrize("name", NAMES)
def test_the_tracks_the_caller_passed_in_are_left_alone(name):
    tracks = given(name)

    spread(tracks)

    assert tracks == QUEUES[name]


def test_an_artist_holding_more_than_half_the_queue_is_refused():
    with pytest.raises(ValueError):
        spread(queue("ora", "ora", "ora", "vek"))


def test_an_empty_queue_stays_empty():
    assert list(spread([])) == []
