"""Behaviour half of the grading suite: must pass before and after the move,
so it touches only what pipeline.py keeps exporting."""

import pytest

from pipeline import Pipeline, RetryPolicy


def test_runs_steps_in_order():
    pipeline = Pipeline().add("double", lambda v: v * 2).add("inc", lambda v: v + 1)

    assert pipeline.run(3) == 7


def test_retries_until_a_step_succeeds():
    calls = []

    def flaky(value):
        calls.append(value)
        if len(calls) < 3:
            raise ValueError("not yet")
        return value

    assert Pipeline(RetryPolicy(attempts=3)).add("flaky", flaky).run(1) == 1
    assert len(calls) == 3


def test_a_step_is_tried_exactly_attempts_times_then_fails():
    calls = []

    def broken(value):
        calls.append(value)
        raise ValueError("always")

    pipeline = Pipeline(RetryPolicy(attempts=2)).add("boom", broken)
    with pytest.raises(RuntimeError, match="step 'boom' failed after 2 attempts"):
        pipeline.run(0)
    assert len(calls) == 2


def test_the_default_policy_tries_three_times_without_waiting():
    policy = Pipeline().policy

    assert policy.attempts == 3
    assert policy.delays() == [0.0, 0.0, 0.0]


def test_delays_grow_linearly_and_skip_the_first_attempt():
    assert RetryPolicy(attempts=3, backoff_s=2.0).delays() == [0.0, 2.0, 4.0]


def test_a_policy_must_allow_at_least_one_attempt():
    with pytest.raises(ValueError, match="attempts must be at least 1"):
        RetryPolicy(attempts=0)
