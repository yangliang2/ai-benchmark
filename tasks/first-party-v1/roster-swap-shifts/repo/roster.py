"""Who is on which shift, for a small on-call rota."""


def new_roster(days):
    """A roster with a shift for each of `days` and nobody on any of them."""
    return {day: [] for day in days}


def days(roster):
    """The roster's days, in the order the roster was set up with."""
    return list(roster)


def who_is_on(roster, day):
    """The people on `day`'s shift, in the order they were put on it."""
    return list(roster[day])


def add_shift(roster, day, name):
    """Put `name` on `day`'s shift, behind whoever is already on it."""
    if name in roster[day]:
        raise ValueError(f"{name} is already on the {day} shift")
    roster[day].append(name)


def drop_shift(roster, day, name):
    """Take `name` off `day`'s shift, leaving the others in their order."""
    if name not in roster[day]:
        raise ValueError(f"{name} is not on the {day} shift")
    roster[day].remove(name)


def describe(roster):
    """One line per day: the day, then who is on it."""
    return [
        f"{day}: {', '.join(names) if names else '(nobody)'}"
        for day, names in roster.items()
    ]
