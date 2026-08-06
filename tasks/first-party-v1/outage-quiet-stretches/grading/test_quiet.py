"""How `quiet` is graded: against the stretches the prompt spells out.

Every decision is stated — how far a fault outside the window counts, what
two overlapping faults amount to, what an empty window and a fully broken one
come back as, which mistake is refused — so the expected stretches are written
out here in full. This is the zero-crux control the charge-sheet task is read
against.
"""

import pytest
from outage import Fault, quiet

FAULTS = [
    Fault("power", 0, 20),
    Fault("disk", 5, 10),
    Fault("dns", 40, 50),
]

# power swallows disk whole, so the two of them are one stretch of downtime
# and there is no quiet minute between them.
NESTED = [Fault("power", 0, 20), Fault("disk", 5, 10)]


def test_a_window_holding_the_whole_run_of_faults():
    assert list(quiet(FAULTS, 0, 60)) == [(20, 40), (50, 60)]


def test_faults_reaching_outside_the_window_count_only_inside_it():
    assert list(quiet(FAULTS, 10, 45)) == [(20, 40)]


def test_a_fault_lying_wholly_after_the_window_is_ignored():
    assert list(quiet(FAULTS, 25, 35)) == [(25, 35)]


def test_a_fault_lying_wholly_before_the_window_is_ignored():
    assert list(quiet(FAULTS, 55, 60)) == [(55, 60)]


def test_overlapping_faults_leave_no_quiet_minute_between_them():
    assert list(quiet(NESTED, 0, 25)) == [(20, 25)]


def test_a_window_nothing_was_broken_in_comes_back_whole():
    assert list(quiet([], 0, 10)) == [(0, 10)]


def test_a_window_every_minute_of_which_was_broken_comes_back_empty():
    assert list(quiet(FAULTS, 0, 20)) == []


def test_a_window_of_no_length_comes_back_empty():
    assert list(quiet(FAULTS, 30, 30)) == []


def test_the_faults_the_caller_passed_in_are_left_alone():
    faults = list(FAULTS)

    quiet(faults, 0, 60)

    assert faults == FAULTS


@pytest.mark.parametrize(("start", "end"), [(30, 25), (0, -1)])
def test_a_window_that_ends_before_it_starts_is_refused(start, end):
    with pytest.raises(ValueError):
        quiet(FAULTS, start, end)
