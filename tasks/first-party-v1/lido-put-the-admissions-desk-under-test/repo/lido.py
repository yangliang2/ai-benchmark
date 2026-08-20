"""The admissions desk of the borough lido.

One rule for the swimmer standing at the desk, and the same rules worked down
a queue of them.
"""

# The three things the water is given over to for an hour at a time.
SESSION_KINDS = ("lane", "family", "club")


def admit(session, swimmer):
    """What the desk says to `swimmer`, presenting at `session`.

    One of "admitted", "waiting" or "refused".
    """
    _check_session(session)
    _check_swimmer(swimmer)
    if session["kind"] == "club" and not swimmer["member"]:
        return "refused"
    if session["kind"] == "lane" and swimmer["age"] < 16:
        return "refused"
    if swimmer["age"] < 8 and not swimmer["accompanied"]:
        return "refused"
    free = session["capacity"] - session["admitted"]
    if not swimmer["member"]:
        # The last place in the water is held back for a member.
        free -= 1
    return "admitted" if free > 0 else "waiting"


def roll_call(session, swimmers):
    """The desk's answer to a whole queue, taken in the order it is standing.

    Gives back the three lists of names — who went in, who is waiting, who was
    turned away — and leaves the session it was handed as it found it.
    """
    standing = dict(session)
    called = {"admitted": [], "waiting": [], "refused": []}
    for swimmer in swimmers:
        decision = admit(standing, swimmer)
        called[decision].append(swimmer["name"])
        if decision == "admitted":
            standing["admitted"] += 1
    return called


def _check_session(session):
    if session["kind"] not in SESSION_KINDS:
        raise ValueError(f"no such session: {session['kind']!r}")
    if session["capacity"] < 1:
        raise ValueError("a session with no places in it is not a session")
    if not 0 <= session["admitted"] <= session["capacity"]:
        raise ValueError("more swimmers in the water than the water holds")


def _check_swimmer(swimmer):
    if swimmer["age"] < 0:
        raise ValueError("nobody is younger than nought")
