import pytest
from cadence import describe, is_a_slot, make, overran_by, slots

BACKUP = make("backup", 1000, 60)


def test_a_schedule_keeps_what_it_was_made_with():
    assert (BACKUP.name, BACKUP.first_due, BACKUP.every) == ("backup", 1000, 60)


def test_a_job_due_never_is_refused():
    with pytest.raises(ValueError):
        make("backup", 1000, 0)


def test_the_slots_start_at_the_first_one_and_step_by_the_interval():
    assert slots(BACKUP, 4) == [1000, 1060, 1120, 1180]


def test_no_slots_are_asked_for_no_slots():
    assert slots(BACKUP, 0) == []


def test_a_negative_number_of_slots_is_refused():
    with pytest.raises(ValueError):
        slots(BACKUP, -1)


def test_a_time_the_interval_lands_on_is_a_slot():
    assert is_a_slot(BACKUP, 1120)


def test_a_time_between_two_slots_is_not_one():
    assert not is_a_slot(BACKUP, 1121)


def test_a_time_before_the_first_slot_is_not_one():
    assert not is_a_slot(BACKUP, 940)


def test_an_overrun_is_how_far_past_the_slot_the_run_went():
    assert overran_by(BACKUP, 1060, 1075) == 15


def test_a_run_that_finished_early_overran_by_a_negative_amount():
    assert overran_by(BACKUP, 1060, 1050) == -10


def test_the_description_names_the_job_and_its_cadence():
    assert describe(BACKUP) == "backup: every 60s from 1000"
