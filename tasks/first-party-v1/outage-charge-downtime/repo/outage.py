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
