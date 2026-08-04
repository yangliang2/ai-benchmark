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


def free(spans, window):
    """The parts of window not covered by any span, ascending and disjoint."""
    window_start, window_end = window
    gaps = []
    cursor = window_start
    for start, end in merge(spans):
        if end <= window_start or start >= window_end:
            continue
        start = max(start, window_start)
        end = min(end, window_end)
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < window_end:
        gaps.append((cursor, window_end))
    return gaps
