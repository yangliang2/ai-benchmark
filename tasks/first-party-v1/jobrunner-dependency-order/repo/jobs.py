"""Job definitions."""


class Job:
    """A named unit of work wrapping a zero-argument action."""

    def __init__(self, name, action):
        self.name = name
        self.action = action

    def run(self):
        """Perform the job's action and return its result."""
        return self.action()
