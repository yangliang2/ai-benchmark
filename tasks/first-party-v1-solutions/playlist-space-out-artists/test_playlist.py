from playlist import Track, by_artist, describe, total_seconds

TRACKS = [
    Track("dawn", "ora", 210),
    Track("dusk", "vek", 180),
    Track("noon", "ora", 240),
]


def test_an_empty_queue_runs_for_no_time():
    assert total_seconds([]) == 0


def test_a_queues_length_is_its_tracks_added_up():
    assert total_seconds(TRACKS) == 630


def test_grouping_keeps_each_artists_tracks_in_the_order_given():
    assert by_artist(TRACKS) == {
        "ora": [TRACKS[0], TRACKS[2]],
        "vek": [TRACKS[1]],
    }


def test_grouping_nothing_gives_no_groups():
    assert by_artist([]) == {}


def test_the_description_numbers_tracks_from_one():
    assert describe(TRACKS) == [
        "1. dawn (ora)",
        "2. dusk (vek)",
        "3. noon (ora)",
    ]
