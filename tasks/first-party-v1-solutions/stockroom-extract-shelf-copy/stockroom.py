"""What sits on which shelf in a small stockroom.

Shelving is a mapping from shelf name to the list of items on that shelf, and
each function here answers with the shelving that results.
"""

from shelving import copied


def place(shelves, item, shelf):
    """The shelving after `item` has been put on `shelf`."""
    placed = copied(shelves)
    placed.setdefault(shelf, [])
    placed[shelf].append(item)
    return placed


def remove(shelves, item, shelf):
    """The shelving after `item` has been taken off `shelf`."""
    left = copied(shelves)
    if item not in left.get(shelf, []):
        raise KeyError(f"{item} is not on {shelf}")
    left[shelf].remove(item)
    return left


def relabel(shelves, shelf, name):
    """The shelving after `shelf` has been renamed to `name`."""
    renamed = copied(shelves)
    if shelf not in renamed:
        raise KeyError(f"no shelf called {shelf}")
    renamed[name] = renamed.pop(shelf)
    return renamed


def move(shelves, item, source, target):
    """The shelving after `item` has moved from `source` to `target`."""
    return place(remove(shelves, item, source), item, target)
