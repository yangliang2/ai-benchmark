"""How long a session stays usable, and when it has stopped being."""

TTL_SECONDS = 900


def is_expired(session, now):
    """Whether `session` has run out of time by `now`."""
    return now - session.started_at >= TTL_SECONDS
