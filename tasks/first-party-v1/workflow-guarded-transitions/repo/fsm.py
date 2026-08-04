"""A minimal finite-state machine."""


class Machine:
    """A current state plus a transition table."""

    def __init__(self, initial, transitions):
        """transitions maps (state, event) to the next state."""
        self.state = initial
        self.transitions = dict(transitions)

    def can_fire(self, event):
        """Whether event has a transition from the current state."""
        return (self.state, event) in self.transitions

    def fire(self, event):
        """Move to the next state for event; ValueError if there is none."""
        try:
            self.state = self.transitions[(self.state, event)]
        except KeyError:
            raise ValueError(
                f"no transition for {event!r} from {self.state!r}"
            ) from None
