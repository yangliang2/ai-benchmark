"""Behaviour half of the grading suite: must pass before and after the rule
table is built, so it pins the severity each event comes back with — including
the ones where two rules match and the order is what answers."""

from alerts import digest, severity


def test_server_errors_page():
    assert severity({"service": "checkout", "status": 503, "latency_ms": 40}) == "page"
    assert severity({"service": "search", "status": 500, "latency_ms": 4100}) == "page"


def test_slow_responses_warn():
    assert severity({"service": "search", "status": 200, "latency_ms": 2000}) == "warn"
    assert severity({"service": "search", "status": 404, "latency_ms": 9000}) == "warn"


def test_client_errors_are_only_a_notice():
    assert severity({"service": "search", "status": 404, "latency_ms": 30}) == "notice"
    assert severity({"service": "search", "status": 400, "latency_ms": 1999}) == "notice"


def test_healthy_traffic_is_ignored():
    assert severity({"service": "search", "status": 200, "latency_ms": 30}) == "ignore"
    assert severity({"service": "search", "status": 399, "latency_ms": 1999}) == "ignore"


def test_health_checks_are_never_reported_however_they_answer():
    """The first rule is first because it has to win: a health check that
    fails, or hangs, is the monitoring talking to itself and is not an
    incident."""
    assert severity({"service": "healthcheck", "status": 503, "latency_ms": 12}) == (
        "ignore"
    )
    assert severity({"service": "healthcheck", "status": 500, "latency_ms": 8000}) == (
        "ignore"
    )
    assert severity({"service": "healthcheck", "status": 404, "latency_ms": 12}) == (
        "ignore"
    )


def test_the_digest_counts_every_severity():
    events = [
        {"service": "checkout", "status": 500, "latency_ms": 10},
        {"service": "healthcheck", "status": 500, "latency_ms": 10},
        {"service": "search", "status": 200, "latency_ms": 3000},
        {"service": "search", "status": 404, "latency_ms": 10},
    ]

    assert digest(events) == {"page": 1, "warn": 1, "notice": 1, "ignore": 1}
