"""Helpers for half-open integer spans: (start, end) pairs covering start
up to but not including end."""


def merge(spans):
    """Collapse overlapping or touching spans into sorted disjoint spans.

    Empty spans (start == end) cover nothing and disappear.
    """
    ordered = sorted((start, end) for start, end in spans if start < end)
    merged = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def total_length(spans):
    """How many integers the spans cover, counting overlaps once."""
    return sum(end - start for start, end in merge(spans))
