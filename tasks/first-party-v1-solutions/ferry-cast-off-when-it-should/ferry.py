"""The village ferry: the jetty, the boat, and what the ferryman calls out."""

from loading import HOLD, SERVE, Line, short_by
from passengers import in_turn, waited_at_least

BOAT_SEATS = 4


class Ferry:
    """Everyone on the jetty, in the order they are taken, and the boat that
    takes `seats` of them across at a time."""

    def __init__(self, waiting, seats=BOAT_SEATS):
        self.seats = seats
        self.waiting = in_turn(waiting)
        self.line = Line(self.waiting, seats)

    def casts_off(self):
        """Whether the ferryman calls the boat away now."""
        return self.line.call() == SERVE

    def waits(self):
        """Whether the boat stays where it is for the moment."""
        return self.line.call() == HOLD

    def aboard(self):
        """Who the boat takes across on this crossing."""
        return list(self.line.load().served)

    def still_on_the_jetty(self):
        """Who the boat leaves behind on this crossing."""
        return list(self.line.load().left)

    def one_crossing(self):
        """Whether everyone on the jetty would go across in one crossing."""
        return len(self.waiting) <= self.seats

    def crowded(self):
        """Whether the jetty is holding two boatloads or more."""
        return len(self.waiting) >= self.seats * 2

    def short_of(self):
        """How many more must come down before the boat is worth calling."""
        return short_by(len(self.waiting), self.seats)

    def impatient(self, now):
        """Who has been on the jetty long enough to say so."""
        return [
            passenger
            for passenger in self.waiting
            if waited_at_least(passenger, now)
        ]

    def announce(self):
        """The lines the ferryman calls out to the jetty."""
        lines = [f"- {passenger.name}" for passenger in self.aboard()]
        if self.casts_off():
            lines.append(f"Away with {len(self.aboard())} of {self.seats}")
        else:
            lines.append(f"Holding for {self.short_of()} more")
        return lines
