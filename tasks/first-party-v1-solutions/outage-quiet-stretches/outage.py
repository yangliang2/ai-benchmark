"""Reading a run of faults as time a service was down."""

from collections import namedtuple

# One fault: what it was called, the minute it started, the minute it ended.
# A fault covers the minutes from `start` up to but not including `end`, so a
# fault that starts and ends in the same minute covers no time at all.
Fault = namedtuple("Fault", "name start end")


def stretch(fault):
    """The minutes `fault` covers, as a range."""
    if fault.end < fault.start:
        raise ValueError(
            f"{fault.name} ended at {fault.end}, before it started at {fault.start}"
        )
    return range(fault.start, fault.end)


def spans(faults):
    """The stretches of downtime the faults add up to.

    Faults that overlap or meet are one stretch, in order, each a (start, end)
    pair. A fault covering no minutes is not a stretch of anything.
    """
    merged = []
    for fault in sorted(faults, key=lambda fault: (fault.start, fault.end)):
        if not stretch(fault):
            continue
        if merged and fault.start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], fault.end))
        else:
            merged.append((fault.start, fault.end))
    return merged


def downtime(faults):
    """How many minutes at least one fault was covering."""
    return sum(end - start for start, end in spans(faults))


def covering(faults, minute):
    """The names of the faults covering `minute`, in alphabetical order."""
    return sorted(fault.name for fault in faults if minute in stretch(fault))


def describe(faults):
    """One line per stretch of downtime."""
    return [f"{start}-{end} ({end - start} min down)" for start, end in spans(faults)]


def quiet(faults, start, end):
    """The stretches of the window from `start` to `end` nothing was covering.

    Walked against `spans`, so faults that overlap are already one stretch of
    downtime by the time this sees them, and each stretch is trimmed to the
    window: one ending before the window opens or starting after it closes
    leaves the window as it found it.
    """
    if end < start:
        raise ValueError(f"a window cannot end at {end}, before it starts at {start}")
    free = []
    at = start
    for down_from, down_to in spans(faults):
        if down_to <= at or down_from >= end:
            continue
        if down_from > at:
            free.append((at, down_from))
        at = max(at, down_to)
        if at >= end:
            break
    if at < end:
        free.append((at, end))
    return free
