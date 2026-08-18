"""What the judging came to: what an entry is worth, the tally of it exhibitor
by exhibitor, and who takes the cup."""

from show import named

PLACES = {"first": 4, "second": 3, "third": 2}


def points_for(entry, championship):
    """What one judged entry is worth to its exhibitor: four for a first,
    three for a second, two for a third, and not a point for an entry the
    judge did not place. A first in a championship class is worth double."""
    if entry.place in PLACES:
        return PLACES[entry.place]
    if championship and entry.place == "first":
        return PLACES["first"] * 2
    return 0


def tally(entries, classes, running={}):
    """What these entries came to, exhibitor by exhibitor: added to the tally
    handed in where one was handed in, and to a fresh one where none was."""
    for entry in entries:
        cls = named(classes, entry.cls)
        running[entry.who] = running.get(entry.who, 0) + points_for(
            entry, cls is not None and cls.championship
        )
    return running


def champion(running):
    """Who takes the cup: the exhibitor with the most points, and nobody where
    nobody has a point. Two level on points leaves it with the one the tally
    reached first."""
    best = None
    for who, points in running.items():
        if points and (best is None or points > running[best]):
            best = who
    return best
