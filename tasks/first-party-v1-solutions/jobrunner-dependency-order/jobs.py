"""Job definitions."""


class Job:
    """A named unit of work wrapping a zero-argument action.

    needs names the jobs that must run first; priority orders jobs that are
    ready at the same time (higher first).
    """

    def __init__(self, name, action, needs=(), priority=0):
        self.name = name
        self.action = action
        self.needs = tuple(needs)
        self.priority = priority

    def run(self):
        """Perform the job's action and return its result."""
        return self.action()
