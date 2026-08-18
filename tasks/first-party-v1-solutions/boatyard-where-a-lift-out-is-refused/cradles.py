"""The frames a hull rests on once it is clear of the water.

The store holds three patterns of frame, and each pattern will only take a
hull up to a certain width. Which one a boat gets is a question about the
frame and about nothing else: it knows nothing about seasons, tides or
standings, and it never says whether a boat is coming out — only which frame
would hold it if it did.
"""

# The widest hull, in centimetres, each pattern of frame will take.
PATTERNS = {"light": 240, "medium": 330, "heavy": 460}


class Cradle:
    """One frame in the store: its pattern, and what is sitting on it."""

    def __init__(self, pattern, holding=None):
        if pattern not in PATTERNS:
            raise ValueError(f"no frame of that pattern: {pattern!r}")
        self.pattern = pattern
        self.holding = holding

    def takes(self, beam_cm):
        """Whether a hull this wide would sit on this frame."""
        return beam_cm <= PATTERNS[self.pattern]

    def __repr__(self):
        return f"Cradle({self.pattern!r}, holding={self.holding!r})"


def cradle_for(cradles, beam_cm):
    """The slightest free frame that would take a hull this wide, or None.

    Slightest first, so a dinghy does not end up on the frame the trawler
    needs. A frame with something on it is not free, however wide it is.
    """
    free = [cradle for cradle in cradles if cradle.holding is None]
    fitting = [cradle for cradle in free if cradle.takes(beam_cm)]
    return min(fitting, key=lambda cradle: PATTERNS[cradle.pattern], default=None)
