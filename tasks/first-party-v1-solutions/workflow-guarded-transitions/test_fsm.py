import pytest
from fsm import Machine

TRANSITIONS = {
    ("locked", "coin"): "unlocked",
    ("unlocked", "push"): "locked",
}


def test_fire_follows_the_transition_table():
    machine = Machine("locked", TRANSITIONS)
    machine.fire("coin")
    assert machine.state == "unlocked"


def test_an_unknown_event_raises():
    with pytest.raises(ValueError):
        Machine("locked", TRANSITIONS).fire("push")


def test_can_fire_checks_without_moving():
    machine = Machine("locked", TRANSITIONS)
    assert machine.can_fire("coin")
    assert not machine.can_fire("push")
    assert machine.state == "locked"
