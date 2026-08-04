import pytest

from fsm import Machine
from tickets import new_ticket

TRANSITIONS = {
    ("locked", "coin"): "unlocked",
    ("unlocked", "push"): "locked",
}


def test_a_machine_carries_a_context_dict():
    assert Machine("locked", TRANSITIONS).context == {}
    machine = Machine("locked", TRANSITIONS, context={"coins": 3})
    assert machine.context == {"coins": 3}


def test_an_unguarded_fire_transitions_and_returns_true():
    machine = Machine("locked", TRANSITIONS)
    assert machine.fire("coin") is True
    assert machine.state == "unlocked"


def test_a_failing_guard_blocks_the_transition():
    machine = Machine("locked", TRANSITIONS, context={"paid": False})
    machine.add_guard("locked", "coin", lambda context: context["paid"])
    assert machine.fire("coin") is False
    assert machine.state == "locked"
    assert machine.history == []


def test_a_passing_guard_lets_the_transition_through():
    machine = Machine("locked", TRANSITIONS, context={"paid": True})
    machine.add_guard("locked", "coin", lambda context: context["paid"])
    assert machine.fire("coin") is True
    assert machine.state == "unlocked"


def test_hooks_run_with_the_context_after_a_successful_fire():
    machine = Machine("locked", TRANSITIONS, context={"count": 0})

    def count(context):
        context["count"] += 1

    machine.add_hook("locked", "coin", count)
    machine.fire("coin")
    assert machine.context["count"] == 1


def test_history_records_successful_fires_in_order():
    machine = Machine("locked", TRANSITIONS)
    machine.fire("coin")
    machine.fire("push")
    assert machine.history == [
        ("locked", "coin", "unlocked"),
        ("unlocked", "push", "locked"),
    ]


def test_an_unknown_event_still_raises():
    with pytest.raises(ValueError):
        Machine("locked", TRANSITIONS).fire("push")


def finished_ticket():
    ticket = new_ticket()
    ticket.fire("triage")
    ticket.fire("start")
    ticket.fire("finish")
    return ticket


def test_a_done_ticket_can_be_reopened():
    ticket = finished_ticket()
    assert ticket.fire("reopen") is True
    assert ticket.state == "in-progress"


def test_the_third_reopen_is_blocked_not_an_error():
    ticket = finished_ticket()
    ticket.fire("reopen")
    ticket.fire("finish")
    ticket.fire("reopen")
    ticket.fire("finish")
    assert ticket.fire("reopen") is False
    assert ticket.state == "done"
    assert ticket.context["reopens"] == 2
