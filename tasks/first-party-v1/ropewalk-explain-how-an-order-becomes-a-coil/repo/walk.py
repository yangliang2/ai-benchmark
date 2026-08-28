"""The walk itself: yarn off the rack, strands on the hooks, a coil at
the end.

A lay is as many strands as its name says, and every strand runs the full
length of the walk — so a length takes its own fathoms off the rack once
per strand. The twist takes up nothing here: the walk lays slack and the
stretch comes out on the hooks.
"""

from typing import Any

import stores
from stores import Yard


def yarn_for(fathoms: int, strands: int) -> int:
    """What a length takes off the rack: the walked fathoms, once per
    strand of the lay."""
    return fathoms * strands


def walk_out(yard: Yard, fathoms: int, strands: int, lay: str) -> dict[str, Any]:
    """Walk one order's length and lay it up into a coil.

    The whole requirement is put against the rack before any bundle comes
    down: an order the rack cannot cover is refused here, whole, and the
    rack is left exactly as it stood.
    """
    needed = yarn_for(fathoms, strands)
    if stores.on_hand(yard) < needed:
        raise ValueError(
            f"the rack holds {stores.on_hand(yard)} fathom(s) of yarn and "
            f"the walk needs {needed}"
        )
    drawn = stores.draw(yard, needed)
    return {
        "fathoms": fathoms,
        "lay": lay,
        "yarn_fathoms": needed,
        "bundles": drawn,
    }
