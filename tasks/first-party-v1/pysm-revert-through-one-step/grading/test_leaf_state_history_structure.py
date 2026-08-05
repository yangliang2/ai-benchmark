"""Structural half of the grading suite: asserts the move really became a step
of its own that both public methods go through, and that reverting no longer
reaches around set_previous_leaf_state. Fails on the pristine repository,
where _move_to_previous_leaf_state does not exist.
"""

import inspect
from typing import NamedTuple

from pysm import Event, State, StateMachine


class Fixture(NamedTuple):
    root: StateMachine
    one: State
    two: State


def machine():
    root = StateMachine("root")
    one, two = State("one"), State("two")
    root.add_state(one, initial=True)
    root.add_state(two)
    root.add_transition(one, two, events=["next"])
    root.initialize()
    return Fixture(root, one, two)


def test_the_move_is_a_step_of_its_own():
    assert callable(StateMachine._move_to_previous_leaf_state)


def test_the_step_returns_the_state_it_moved_to():
    fixture = machine()
    fixture.root.dispatch(Event("next"))

    assert fixture.root._move_to_previous_leaf_state(None) is fixture.one


def test_the_step_returns_none_when_there_is_no_history():
    fixture = machine()

    assert fixture.root._move_to_previous_leaf_state(None) is None
    assert fixture.root.leaf_state is fixture.one


def test_both_public_methods_go_through_the_step(monkeypatch):
    """A real delegation, not a step added alongside the old bodies: with it
    replaced by one that moves nothing and reports no history, neither public
    method may move the machine."""
    seen = []
    monkeypatch.setattr(
        StateMachine,
        "_move_to_previous_leaf_state",
        lambda self, event: seen.append(event),
    )
    fixture = machine()
    fixture.root.dispatch(Event("next"))
    reason = Event("undo")

    fixture.root.set_previous_leaf_state(reason)
    fixture.root.revert_to_previous_leaf_state()

    assert seen == [reason, None]
    assert fixture.root.leaf_state is fixture.two


def test_reverting_no_longer_reaches_around_the_other_method():
    """The call, not the docstring: the two methods may still describe each
    other, they just may not be implemented through each other."""
    source = inspect.getsource(StateMachine.revert_to_previous_leaf_state)

    assert "self.set_previous_leaf_state(" not in source
