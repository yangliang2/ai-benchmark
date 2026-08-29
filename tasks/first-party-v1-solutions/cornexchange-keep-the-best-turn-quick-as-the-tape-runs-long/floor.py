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

        The tape is run through once, front to back: the cheapest call
        heard so far is carried along, and each new call is set against it,
        so the whole day is reckoned in one winding-through rather than
        wound back for every pair. The carried call is only replaced by a
        strictly cheaper one and the best turn only by a strictly larger
        gain, which is what keeps ties on the earliest hours — the same
        turns the pair-by-pair reckoning named.
        """
        best = None
        best_gain = 0
        cheapest = None
        for place in range(self._tape.length()):
            hour, price = self._tape.call_at(place)
            if cheapest is not None:
                gain = price - cheapest[1]
                if gain > best_gain:
                    best, best_gain = (cheapest[0], hour, gain), gain
            if cheapest is None or price < cheapest[1]:
                cheapest = (hour, price)
        return best
