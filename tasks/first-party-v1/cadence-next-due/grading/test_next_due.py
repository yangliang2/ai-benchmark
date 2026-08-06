"""How `next_due` is graded: by where the job is due after a long run.

The near half — a run that finishes before its next slot comes round is next
due at that slot — is what a reader of the change checks, and it is the only
case a job that runs to time ever takes. An answer written as "the next slot
if we are still in time, otherwise an interval from now" gets every one of
those right, and gets the schedule right for as long as nothing overruns.
The first run that outlasts a slot moves the job off the grid it was made
with, and it never comes back: the slot after that is wrong too, and so is
every slot after that. Nothing at the time of the wrong answer says it was
wrong — the job runs, an interval later it runs again — and what is lost is
the cadence, several runs downstream.

Every expected time here is written out, so a rewritten `slots` or
`is_a_slot` cannot make a drifting answer look on time.
"""

import pytest
from cadence import make, next_due

# Due at 1000 and every minute after: 1000, 1060, 1120, 1180, 1240, ...
BACKUP = make("backup", 1000, 60)


# --- the near half: runs that keep up ------------------------------------------


def test_a_run_that_finished_on_time_is_next_due_at_the_next_slot():
    assert next_due(BACKUP, 1000, 1000) == 1060


def test_a_run_that_finished_late_but_in_time_is_next_due_at_the_next_slot():
    assert next_due(BACKUP, 1060, 1090) == 1120


def test_a_run_that_finished_a_second_before_its_next_slot_still_makes_it():
    assert next_due(BACKUP, 1060, 1119) == 1120


def test_the_first_slot_is_a_slot_like_any_other():
    assert next_due(BACKUP, 1000, 1042) == 1060


# --- the far half: a run that outlasts a slot ----------------------------------


def test_a_run_that_outlasted_its_next_slot_misses_it_rather_than_making_it_up():
    assert next_due(BACKUP, 1000, 1075) == 1120


def test_a_run_that_outlasted_several_slots_misses_all_of_them():
    assert next_due(BACKUP, 1000, 1310) == 1360


def test_a_run_that_finished_exactly_on_a_later_slot_is_due_at_the_one_after():
    assert next_due(BACKUP, 1000, 1180) == 1240


def test_the_job_is_back_on_its_own_cadence_the_run_after_an_overrun():
    after_the_overrun = next_due(BACKUP, 1000, 1310)

    assert next_due(BACKUP, after_the_overrun, 1365) == 1420


def test_a_stretch_of_runs_with_one_overrun_stays_on_the_schedules_own_slots():
    due_at, seen = 1000, []

    for finished in (1005, 1100, 1301, 1362, 1500):
        due_at = next_due(BACKUP, due_at, finished)
        seen.append(due_at)

    assert seen == [1060, 1120, 1360, 1420, 1540]


def test_an_overrun_of_many_intervals_lands_on_the_next_slot_after_it():
    assert next_due(BACKUP, 1000, 4321) == 4360


def test_a_schedule_of_its_own_keeps_its_own_grid():
    hourly = make("sweep", 0, 3600)

    assert next_due(hourly, 0, 5400) == 7200


# --- what a due time has to be -------------------------------------------------


def test_a_due_time_that_is_not_one_of_the_schedules_slots_is_refused():
    with pytest.raises(ValueError):
        next_due(BACKUP, 1030, 1040)


def test_a_due_time_before_the_first_slot_is_refused():
    with pytest.raises(ValueError):
        next_due(BACKUP, 940, 1000)


def test_a_run_that_finished_before_it_was_due_is_refused():
    with pytest.raises(ValueError):
        next_due(BACKUP, 1060, 1059)
