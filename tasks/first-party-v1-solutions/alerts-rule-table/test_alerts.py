from alerts import digest, severity


def test_server_errors_page():
    assert severity({"service": "checkout", "status": 503, "latency_ms": 40}) == "page"


def test_slow_responses_warn():
    assert severity({"service": "search", "status": 200, "latency_ms": 4100}) == "warn"


def test_client_errors_are_only_a_notice():
    assert severity({"service": "search", "status": 404, "latency_ms": 30}) == "notice"


def test_healthy_traffic_is_ignored():
    assert severity({"service": "search", "status": 200, "latency_ms": 30}) == "ignore"


def test_health_checks_are_ignored():
    assert severity({"service": "healthcheck", "status": 200, "latency_ms": 12}) == (
        "ignore"
    )


def test_the_digest_counts_every_severity():
    events = [
        {"service": "checkout", "status": 500, "latency_ms": 10},
        {"service": "search", "status": 200, "latency_ms": 3000},
        {"service": "search", "status": 404, "latency_ms": 10},
        {"service": "search", "status": 200, "latency_ms": 10},
    ]

    assert digest(events) == {"page": 1, "warn": 1, "notice": 1, "ignore": 1}
