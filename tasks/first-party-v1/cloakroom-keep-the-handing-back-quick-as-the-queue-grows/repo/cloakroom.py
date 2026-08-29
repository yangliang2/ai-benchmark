"""The cloakroom hatch, and the evening's handing back over it."""


class Cloakroom:
    """The room behind the hatch: the rail, and how the queue is answered."""

    def __init__(self, rail):
        self._rail = rail

    def coat_for(self, ticket):
        """The description of the coat checked under this ticket.

        The rail is walked from the first peg. None when no coat on the
        rail carries the ticket. The room pins one ticket to one coat, so
        the first match is the only one.
        """
        for peg in self._rail.pegs():
            coat = self._rail.take_down(peg)
            if coat.ticket == ticket:
                return coat.description
        return None

    def hand_back(self, tickets):
        """One line per asking: (ticket presented, description to fetch).

        The queue at the hatch, answered in the order it formed.
        """
        return [(ticket, self.coat_for(ticket)) for ticket in tickets]
