from jobs import Job


def test_a_job_runs_its_action():
    log = []
    job = Job("greet", lambda: log.append("hi"))
    job.run()
    assert log == ["hi"]


def test_a_job_returns_its_action_result():
    assert Job("answer", lambda: 42).run() == 42
