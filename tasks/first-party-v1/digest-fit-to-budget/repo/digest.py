"""Cutting a long run of log entries down to something a person will read."""

from collections import namedtuple

# One entry in the run: when it happened, what it said, and whether whoever
# wrote it marked it as something not to be cut.
Entry = namedtuple("Entry", "at text important")

# What stands in a digest for a run of entries left out of it.
Gap = namedtuple("Gap", "dropped")


def entries_only(items):
    """The entries of a digest, with its gaps taken out."""
    return [item for item in items if not isinstance(item, Gap)]


def stands_for(items):
    """How many entries a digest stands for: the ones it keeps, plus the ones
    its gaps count for."""
    return sum(item.dropped if isinstance(item, Gap) else 1 for item in items)


def must_keep(entries):
    """The entries a digest holds whatever else it leaves out: the ones marked
    important, and the first and the last of the run."""
    if not entries:
        return []
    kept = {0, len(entries) - 1}
    kept.update(position for position, entry in enumerate(entries) if entry.important)
    return [entries[position] for position in sorted(kept)]


def render(items):
    """One line per item; a gap says how many entries it stands in for."""
    return [
        f"... {item.dropped} more"
        if isinstance(item, Gap)
        else f"{item.at} {item.text}"
        for item in items
    ]
