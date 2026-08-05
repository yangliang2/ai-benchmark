"""Building listening queues out of a library of tracks."""

from collections import namedtuple

# One track: what it is called, who recorded it, how long it runs.
Track = namedtuple("Track", "title artist seconds")


def total_seconds(tracks):
    """How long `tracks` run in total."""
    return sum(track.seconds for track in tracks)


def by_artist(tracks):
    """The tracks grouped by artist, each group in the order given."""
    grouped = {}
    for track in tracks:
        grouped.setdefault(track.artist, []).append(track)
    return grouped


def describe(tracks):
    """One line per track: its position, its title, who recorded it."""
    return [
        f"{position}. {track.title} ({track.artist})"
        for position, track in enumerate(tracks, start=1)
    ]
