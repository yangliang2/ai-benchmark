"""How `blame` is graded: by what a charge sheet has to be, not by one sheet.

Which of the faults covering a contested minute is charged for it is the
decision the prompt deliberately leaves open — several policies satisfy the
rules for the same faults and every one of them is a correct answer — so what
is checked is that the charges add up to the downtime, that nobody is charged
for a minute they were not covering, that a minute only one fault was over
lands on that fault, and that the sheet does not turn on the order the faults
arrived in.

Every yardstick here is a literal written out beside the faults it belongs to,
rather than read back through `spans` or `downtime`. A charge sheet that came
with a rewritten notion of downtime would otherwise be graded against its own
arithmetic.
"""

from typing import NamedTuple

import pytest
from outage import Fault, blame


class Case(NamedTuple):
    """One run of faults and everything known about it independently.

    `covers` is how many minutes each fault covers on its own, `alone` how
    many of those no other fault was over, and `total` how many minutes at
    least one fault was covering.
    """

    faults: list
    total: int
    covers: dict
    alone: dict


CASES = {
    # One fault, so every minute of it is that fault's own.
    "single": Case(
        faults=[Fault("power", 0, 10)],
        total=10,
        covers={"power": 10},
        alone={"power": 10},
    ),
    # disk sits wholly inside power: it has no minute of its own at all, and
    # the whole of its stretch is contested.
    "nested": Case(
        faults=[Fault("power", 0, 20), Fault("disk", 5, 10)],
        total=20,
        covers={"power": 20, "disk": 5},
        alone={"power": 15, "disk": 0},
    ),
    # Half of each is its own and the five minutes in the middle are shared.
    "staggered": Case(
        faults=[Fault("net", 0, 10), Fault("dns", 5, 15)],
        total=15,
        covers={"net": 10, "dns": 10},
        alone={"net": 5, "dns": 5},
    ),
    # Two separate contests along one stretch, with a fault in the middle
    # that is contested at both ends.
    "chain": Case(
        faults=[Fault("power", 0, 6), Fault("net", 4, 10), Fault("dns", 8, 14)],
        total=14,
        covers={"power": 6, "net": 6, "dns": 6},
        alone={"power": 4, "net": 2, "dns": 4},
    ),
    # Nothing shared: the sheet is settled before any policy is needed.
    "apart": Case(
        faults=[Fault("cache", 0, 5), Fault("queue", 10, 15)],
        total=10,
        covers={"cache": 5, "queue": 5},
        alone={"cache": 5, "queue": 5},
    ),
    # A fault that came and went inside the same minute.
    "blip": Case(
        faults=[Fault("power", 0, 10), Fault("blip", 3, 3)],
        total=10,
        covers={"power": 10, "blip": 0},
        alone={"power": 10, "blip": 0},
    ),
}

NAMES = sorted(CASES)


def given(name):
    """One run of faults, handed over as a list of its own, so that a solution
    which sorts or consumes what it was given fails the one rule about that
    and not the ones about something else."""
    return list(CASES[name].faults)


@pytest.mark.parametrize("name", NAMES)
def test_every_fault_has_a_line_and_nobody_else_does(name):
    assert dict(blame(given(name))).keys() == CASES[name].covers.keys()


@pytest.mark.parametrize("name", NAMES)
def test_the_charges_add_up_to_the_downtime(name):
    """The rule that makes this a division of the downtime rather than a
    report of it: an overlapping minute is charged once, not once per fault
    that was over it."""
    sheet = blame(given(name))

    assert sum(sheet[fault] for fault in CASES[name].covers) == CASES[name].total


@pytest.mark.parametrize("name", NAMES)
def test_nobody_is_charged_for_a_minute_they_were_not_covering(name):
    sheet = blame(given(name))

    for fault, covered in CASES[name].covers.items():
        assert sheet[fault] <= covered


@pytest.mark.parametrize("name", NAMES)
def test_a_minute_only_one_fault_was_covering_is_charged_to_that_fault(name):
    """There is nobody else to charge it to, so however the contested minutes
    are shared out, a fault's own minutes are already its own."""
    sheet = blame(given(name))

    for fault, own in CASES[name].alone.items():
        assert sheet[fault] >= own


@pytest.mark.parametrize("name", NAMES)
def test_the_charges_are_whole_minutes(name):
    """Stated in the brief, so graded: a minute goes to one fault, and half a
    minute each to two of them is not a division of it.

    Graded on the charge rather than on the type carrying it: a sheet that
    counted in floats and came out whole everywhere has divided the minutes
    exactly as the brief asks, and 3.0 minutes is three minutes.
    """
    sheet = blame(given(name))

    for fault in CASES[name].covers:
        assert sheet[fault] == int(sheet[fault])


@pytest.mark.parametrize("name", NAMES)
def test_the_order_the_faults_arrived_in_does_not_change_the_sheet(name):
    faults = given(name)

    assert dict(blame(list(reversed(faults)))) == dict(blame(faults))
    assert dict(blame(faults[1:] + faults[:1])) == dict(blame(faults))


@pytest.mark.parametrize("name", NAMES)
def test_the_faults_the_caller_passed_in_are_left_alone(name):
    faults = given(name)

    blame(faults)

    assert faults == CASES[name].faults


def test_a_fault_that_covered_no_minutes_is_charged_nothing():
    assert blame(given("blip"))["blip"] == 0


def test_no_faults_are_charged_nothing():
    assert dict(blame([])) == {}


@pytest.mark.parametrize(
    "fault", [Fault("muddle", 9, 4), Fault("backwards", 0, -1)]
)
def test_a_fault_that_ended_before_it_started_is_refused(fault):
    with pytest.raises(ValueError):
        blame([Fault("power", 0, 10), fault])
