"""A tiny step pipeline."""

import time

from retry import RetryPolicy


class Pipeline:
    """Named steps applied in order, each retried under one policy."""

    def __init__(self, policy=None):
        self.policy = policy if policy is not None else RetryPolicy()
        self.steps = []

    def add(self, name, step):
        """Append one named step: a callable from value to value."""
        self.steps.append((name, step))
        return self

    def run(self, value):
        """Thread value through every step, retrying failures per the policy."""
        for name, step in self.steps:
            value = self._run_step(name, step, value)
        return value

    def _run_step(self, name, step, value):
        error = None
        for delay in self.policy.delays():
            if delay:
                time.sleep(delay)
            try:
                return step(value)
            except Exception as exc:  # noqa: BLE001 - retrying is this wrapper's job
                error = exc
        raise RuntimeError(
            f"step {name!r} failed after {self.policy.attempts} attempts"
        ) from error
