"""Sorting task lines into board lanes."""

from tasktrack import parse_task

LANES = ("done", "urgent", "soon", "later")


def lane_for(line):
    """Which lane one task line belongs to; done wins over urgency."""
    title, priority, tags, done = parse_task(line)
    if done:
        return "done"
    if priority == 1:
        return "urgent"
    if priority == 2:
        return "soon"
    return "later"


def board(lines):
    """Lane -> titles, every lane present, input order kept."""
    lanes = {lane: [] for lane in LANES}
    for line in lines:
        title, priority, tags, done = parse_task(line)
        lanes[lane_for(line)].append(title)
    return lanes
