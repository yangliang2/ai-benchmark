# sessions

Standard-library sign-in sessions. Times are whole seconds on whatever clock
the caller passes in as `now`.

- `Session(token, user, started_at)` — one sign-in
- `TTL_SECONDS` — how long a session stays usable
- `active(sessions, now)` — the ones still usable
- `resolve(sessions, token, now)` — look one up by token
- `prune(sessions, now)` — the ones worth keeping, oldest first
- `seconds_left(session, now)` — how long one has left

Run the tests with `pytest`.
