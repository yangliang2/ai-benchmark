"""How loudly an incoming monitoring event should be reported."""


def _is_healthcheck(event):
    return event["service"] == "healthcheck"


def _is_server_error(event):
    return event["status"] >= 500


def _is_slow(event):
    return event["latency_ms"] >= 2000


def _is_client_error(event):
    return event["status"] >= 400


RULES = (
    (_is_healthcheck, "ignore"),
    (_is_server_error, "page"),
    (_is_slow, "warn"),
    (_is_client_error, "notice"),
)


def severity(event):
    """The severity of one event: page, warn, notice or ignore.

    The first rule that matches decides.
    """
    for matches, level in RULES:
        if matches(event):
            return level
    return "ignore"


def digest(events):
    """How many events of each severity, loudest severity first."""
    counts = {"page": 0, "warn": 0, "notice": 0, "ignore": 0}
    for event in events:
        counts[severity(event)] += 1
    return counts
