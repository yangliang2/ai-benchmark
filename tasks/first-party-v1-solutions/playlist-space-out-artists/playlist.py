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


def spread(tracks):
    """The tracks in an order that never plays one artist twice running.

    Whoever has the most tracks still waiting goes next, the artist just
    played excepted: it is leaving the busiest artist until last that strands
    their remaining tracks side by side.
    """
    waiting = by_artist(tracks)
    if any(len(group) > (len(tracks) + 1) // 2 for group in waiting.values()):
        raise ValueError("one artist holds too many tracks to be spaced out")
    order = []
    played = None
    while waiting:
        artist = max(
            (name for name in waiting if name != played),
            key=lambda name: len(waiting[name]),
        )
        order.append(waiting[artist].pop(0))
        if not waiting[artist]:
            del waiting[artist]
        played = artist
    return order
