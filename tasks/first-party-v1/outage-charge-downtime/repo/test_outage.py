import pytest
from outage import Fault, covering, describe, downtime, spans, stretch

FAULTS = [
    Fault("power", 0, 20),
    Fault("disk", 5, 10),
    Fault("dns", 40, 50),
]


def test_a_fault_covers_the_minutes_from_its_start_up_to_its_end():
    assert list(stretch(Fault("power", 0, 3))) == [0, 1, 2]


def test_a_fault_that_ends_where_it_started_covers_nothing():
    assert list(stretch(Fault("blip", 7, 7))) == []


def test_a_fault_that_ends_before_it_started_is_refused():
    with pytest.raises(ValueError):
        stretch(Fault("muddle", 9, 4))


def test_overlapping_faults_are_one_stretch_of_downtime():
    assert spans(FAULTS) == [(0, 20), (40, 50)]


def test_faults_that_meet_are_one_stretch_too():
    assert spans([Fault("one", 0, 5), Fault("two", 5, 9)]) == [(0, 9)]


def test_no_faults_means_no_downtime():
    assert spans([]) == []
    assert downtime([]) == 0


def test_downtime_counts_an_overlapping_minute_once():
    assert downtime(FAULTS) == 30


def test_who_was_covering_a_minute():
    assert covering(FAULTS, 7) == ["disk", "power"]
    assert covering(FAULTS, 25) == []


def test_the_description_has_a_line_per_stretch():
    assert describe(FAULTS) == ["0-20 (20 min down)", "40-50 (10 min down)"]
