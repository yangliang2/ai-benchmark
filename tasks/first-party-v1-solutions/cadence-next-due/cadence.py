"""When a repeating job is due to run.

Times are whole seconds on one clock. Nothing here knows about calendars,
time zones or wall clocks: a schedule is a first time and an interval, and
every time the job is due is one of the times that interval lands on.
"""

from collections import namedtuple

# A job due every `every` seconds, the first time at `first_due`.
Schedule = namedtuple("Schedule", "name first_due every")


def make(name, first_due, every):
    """A schedule for `name`, first due at `first_due`, every `every` seconds."""
    if every < 1:
        raise ValueError(f"a job due every {every} seconds is never due again")
    return Schedule(name, first_due, every)


def slots(schedule, count):
    """The first `count` times the job is due, earliest first."""
    if count < 0:
        raise ValueError(f"a schedule cannot have {count} slots")
    return [schedule.first_due + step * schedule.every for step in range(count)]


def is_a_slot(schedule, when):
    """Whether `when` is one of the times this schedule makes the job due."""
    if when < schedule.first_due:
        return False
    return (when - schedule.first_due) % schedule.every == 0


def overran_by(schedule, due_at, ran_at):
    """How long past its slot a run due at `due_at` and finished at `ran_at`
    went. Negative when it finished before it was even due."""
    return ran_at - due_at


def describe(schedule):
    """A printable line naming the job and how often it runs."""
    return f"{schedule.name}: every {schedule.every}s from {schedule.first_due}"


def next_due(schedule, due_at, ran_at):
    """When the job is next due after a run due at `due_at` that finished at
    `ran_at`.

    The answer is walked forward along the schedule's own slots rather than
    measured from `ran_at`, so a run that outlasted a slot misses it and the
    job stays on the grid it was made with.
    """
    if not is_a_slot(schedule, due_at):
        raise ValueError(f"{due_at} is not one of {schedule.name}'s slots")
    if ran_at < due_at:
        raise ValueError(
            f"{schedule.name} cannot have finished at {ran_at}, before it was "
            f"due at {due_at}"
        )
    following = due_at + schedule.every
    while following <= ran_at:
        following += schedule.every
    return following
