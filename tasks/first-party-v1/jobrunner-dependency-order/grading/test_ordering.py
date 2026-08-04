import pytest
from jobs import Job
from runner import execution_order, run_all


def job(name, needs=(), priority=0, log=None):
    def action():
        if log is not None:
            log.append(name)

    return Job(name, action, needs=needs, priority=priority)


def test_a_job_runs_after_everything_it_needs():
    order = execution_order(
        [
            job("deploy", needs=["build", "check"]),
            job("build"),
            job("check", needs=["build"]),
        ]
    )
    assert order == ["build", "check", "deploy"]


def test_ready_jobs_run_highest_priority_first():
    order = execution_order([job("a"), job("b", priority=5), job("c", priority=1)])
    assert order == ["b", "c", "a"]


def test_equal_priorities_break_ties_alphabetically():
    order = execution_order([job("b"), job("a"), job("c")])
    assert order == ["a", "b", "c"]


def test_priority_never_overrides_a_dependency():
    order = execution_order(
        [
            job("late", priority=99, needs=["early"]),
            job("early", priority=0),
            job("other", priority=50),
        ]
    )
    assert order == ["other", "early", "late"]


def test_an_unknown_dependency_is_named_in_the_error():
    with pytest.raises(ValueError, match="ghost"):
        execution_order([job("build", needs=["ghost"])])


def test_a_dependency_cycle_is_reported_as_one():
    with pytest.raises(ValueError, match="cycle"):
        execution_order([job("a", needs=["b"]), job("b", needs=["a"])])


def test_a_self_dependency_is_a_cycle():
    with pytest.raises(ValueError, match="cycle"):
        execution_order([job("a", needs=["a"])])


def test_run_all_executes_actions_in_dependency_order():
    log = []
    jobs = [
        job("deploy", needs=["check"], log=log),
        job("check", needs=["build"], log=log),
        job("build", log=log),
    ]
    assert run_all(jobs) == ["build", "check", "deploy"]
    assert log == ["build", "check", "deploy"]
