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


def with_swap(roster, day, leaving, arriving):
    """A new roster with `arriving` standing where `leaving` stood on `day`.

    Every day gets a list of its own, not just the mapping: a roster sharing
    one day's people with the roster it was made from is a roster whose owner
    can be edited from somewhere else.
    """
    shift = roster[day]
    if leaving not in shift:
        raise ValueError(f"{leaving} is not on the {day} shift")
    if arriving in shift:
        raise ValueError(f"{arriving} is already on the {day} shift")
    swapped = {name: list(people) for name, people in roster.items()}
    swapped[day][swapped[day].index(leaving)] = arriving
    return swapped
