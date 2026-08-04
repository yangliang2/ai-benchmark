"""A minimal finite-state machine with guards, hooks and history."""


class Machine:
    """A current state, a transition table, and a context guards and hooks
    read and write."""

    def __init__(self, initial, transitions, context=None):
        """transitions maps (state, event) to the next state."""
        self.state = initial
        self.transitions = dict(transitions)
        self.context = {} if context is None else context
        self.history = []
        self._guards = {}
        self._hooks = {}

    def can_fire(self, event):
        """Whether event has a transition from the current state."""
        return (self.state, event) in self.transitions

    def add_guard(self, state, event, predicate):
        """Only let (state, event) fire when predicate(context) is truthy."""
        self._guards.setdefault((state, event), []).append(predicate)

    def add_hook(self, state, event, callback):
        """Call callback(context) after (state, event) fires."""
        self._hooks.setdefault((state, event), []).append(callback)

    def fire(self, event):
        """Fire event: True if the transition ran, False if a guard blocked
        it; ValueError if there is no transition from the current state."""
        key = (self.state, event)
        try:
            target = self.transitions[key]
        except KeyError:
            raise ValueError(
                f"no transition for {event!r} from {self.state!r}"
            ) from None
        if not all(guard(self.context) for guard in self._guards.get(key, [])):
            return False
        before = self.state
        self.state = target
        self.history.append((before, event, target))
        for hook in self._hooks.get(key, []):
            hook(self.context)
        return True
