"""Sign-in sessions and how long each one stays usable."""

from expiry import TTL_SECONDS, is_expired


class Session:
    """One sign-in: who it is for, and the moment it started."""

    def __init__(self, token, user, started_at):
        self.token = token
        self.user = user
        self.started_at = started_at

    def __repr__(self):
        return f"Session({self.token!r}, {self.user!r}, {self.started_at})"


def active(sessions, now):
    """The sessions still usable at `now`."""
    return [session for session in sessions if not is_expired(session, now)]


def resolve(sessions, token, now):
    """The session `token` names, as long as it is still usable at `now`."""
    for session in sessions:
        if session.token == token:
            if is_expired(session, now):
                raise KeyError(f"session {token} has expired")
            return session
    raise KeyError(f"no session {token}")


def prune(sessions, now):
    """The sessions worth keeping at `now`, oldest first."""
    kept = [session for session in sessions if not is_expired(session, now)]
    return sorted(kept, key=lambda session: session.started_at)


def seconds_left(session, now):
    """How long `session` has left at `now`, never less than nothing."""
    return max(0, TTL_SECONDS - (now - session.started_at))
