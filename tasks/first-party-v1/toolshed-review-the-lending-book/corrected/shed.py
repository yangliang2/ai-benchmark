"""The shed itself: the racks, and the tools that live on each of them."""

RACKS = ("bench", "wall", "floor")


class Tool:
    """One tool of the shed, as the rack list has it."""

    def __init__(self, label, rack):
        self.label = label
        self.rack = rack


def on_rack(tools, rack):
    """Every tool of this rack, in the order the rack list has them."""
    return [tool for tool in tools if tool.rack == rack]


def by_rack(tools):
    """The tools of the shed under the rack each belongs to. A rack holds as
    many tools as it holds, so each collects a list of its own."""
    racked = {}
    for tool in tools:
        racked.setdefault(tool.rack, []).append(tool)
    return racked
