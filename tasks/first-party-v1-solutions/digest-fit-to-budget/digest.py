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


def _laid_out(entries, kept):
    """The digest that keeps exactly the entries at the positions in `kept`."""
    digested = []
    dropped = 0
    for position, entry in enumerate(entries):
        if position not in kept:
            dropped += 1
            continue
        if dropped:
            digested.append(Gap(dropped))
            dropped = 0
        digested.append(entry)
    if dropped:
        digested.append(Gap(dropped))
    return digested


def digest(entries, budget):
    """The run cut down to `budget` places, gaps counting as places.

    The policy chosen for what to keep beyond what has to be kept: the end of
    the run, on the grounds that whoever opens a digest of a failed job is
    looking at what it was doing when it stopped. Walked from the last entry
    backwards, keeping each entry the budget still has room for — and room is
    measured against the digest that would result, because a gap occupies a
    place of its own and an entry kept out of the middle of a stretch splits
    one gap into two.

    One pass answers the rule about being as full as the budget allows:
    keeping more entries never shortens a digest, so an entry that did not fit
    earlier in the walk does not fit later in it either.
    """
    if not entries:
        return []
    kept = {0, len(entries) - 1}
    kept.update(position for position, entry in enumerate(entries) if entry.important)
    least = len(_laid_out(entries, kept))
    if least > budget:
        raise ValueError(
            f"a digest of these {len(entries)} entries needs at least {least} "
            f"places, and the budget is {budget}"
        )
    for position in reversed(range(len(entries))):
        if position in kept:
            continue
        if len(_laid_out(entries, kept | {position})) <= budget:
            kept.add(position)
    return _laid_out(entries, kept)
