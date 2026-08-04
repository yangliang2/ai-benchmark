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


def test_delays_grow_linearly():
    assert RetryPolicy(attempts=3, backoff_s=2.0).delays() == [0.0, 2.0, 4.0]
