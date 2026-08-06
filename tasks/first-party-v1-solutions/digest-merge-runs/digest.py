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


def merge_runs(left, right):
    """The two runs as one run in time order, and what the two had in common.

    The common entries are matched off one at a time rather than through a
    set, so that a message logged twice inside one run stays there twice: what
    makes two entries one entry is the whole of what an entry is, and two runs
    sharing a message at one moment say nothing about the same message at
    another.
    """
    for name, run in (("left", left), ("right", right)):
        for earlier, later in zip(run, run[1:]):
            if later.at < earlier.at:
                raise ValueError(
                    f"the {name} run has an entry at {later.at} following one "
                    f"at {earlier.at}, so it is not in time order"
                )
    waiting = list(right)
    shared = []
    for entry in left:
        if entry in waiting:
            waiting.remove(entry)
            shared.append(entry)
    merged = []
    for entry in left:
        while waiting and waiting[0].at < entry.at:
            merged.append(waiting.pop(0))
        merged.append(entry)
    merged.extend(waiting)
    return merged, shared
