"""The retry policy pipelines run their steps under."""


class RetryPolicy:
    """How often a failing step is retried, and how long to wait in between."""

    def __init__(self, attempts=3, backoff_s=0.0):
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self.attempts = attempts
        self.backoff_s = backoff_s

    def delays(self):
        """Seconds to wait before each attempt: nothing before the first."""
        return [self.backoff_s * n for n in range(self.attempts)]
