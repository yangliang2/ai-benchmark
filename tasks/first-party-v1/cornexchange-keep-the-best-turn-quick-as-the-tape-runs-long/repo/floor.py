"""The floor's reckoning over the day's tape."""


class Floor:
    """The exchange floor: the day's tape, and the reckoning the clerks
    are asked for when the floor empties."""

    def __init__(self, tape):
        self._tape = tape

    def best_turn(self):
        """The best turn the day offered: (hour bought, hour sold, gain).

        A turn buys at one call and sells at a later one, and the best
        turn is the largest gain to be had that way. Between turns of
        equal gain, the earliest buying hour, and between those the
        earliest selling hour. None when no later call ever priced above
        an earlier one.
        """
        best = None
        best_gain = 0
        for place in range(self._tape.length()):
            bought_hour, bought = self._tape.call_at(place)
            for later in range(place + 1, self._tape.length()):
                sold_hour, sold = self._tape.call_at(later)
                gain = sold - bought
                if gain > best_gain:
                    best, best_gain = (bought_hour, sold_hour, gain), gain
        return best
