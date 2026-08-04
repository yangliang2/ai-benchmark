from jobs import Job
from runner import run_all


def test_runs_jobs_in_the_order_given():
    log = []
    jobs = [
        Job("first", lambda: log.append("first")),
        Job("second", lambda: log.append("second")),
    ]
    assert run_all(jobs) == ["first", "second"]
    assert log == ["first", "second"]
