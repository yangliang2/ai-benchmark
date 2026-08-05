"""How shelving is copied before it is changed."""


def copied(shelves):
    """A copy of `shelves` that can be changed without touching the original."""
    return {name: list(items) for name, items in shelves.items()}
