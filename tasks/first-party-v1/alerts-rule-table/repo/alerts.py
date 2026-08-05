"""How loudly an incoming monitoring event should be reported."""


def severity(event):
    """The severity of one event: page, warn, notice or ignore.

    The first rule that matches decides.
    """
    if event["service"] == "healthcheck":
        return "ignore"
    elif event["status"] >= 500:
        return "page"
    elif event["latency_ms"] >= 2000:
        return "warn"
    elif event["status"] >= 400:
        return "notice"
    else:
        return "ignore"


def digest(events):
    """How many events of each severity, loudest severity first."""
    counts = {"page": 0, "warn": 0, "notice": 0, "ignore": 0}
    for event in events:
        counts[severity(event)] += 1
    return counts
