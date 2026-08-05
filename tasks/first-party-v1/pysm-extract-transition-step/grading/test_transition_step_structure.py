"""Structural half of the grading suite: asserts the transition sequence
really moved into a method of its own and that `dispatch` routes through it.
Fails on the pristine repository, where `_perform_transition` does not exist.
"""

import inspect
from typing import NamedTuple

from pysm import Event, State, StateMachine


class Fixture(NamedTuple):
    root: StateMachine
    typing: State
    idle: State


def machine():
    root = StateMachine("root")
    typing, idle = State("typing"), State("idle")
    root.add_state(typing, initial=True)
    root.add_state(idle)
    root.add_transition(typing, idle, events=["pause"])
    root.initialize()
    return Fixture(root, typing, idle)


def test_the_transition_sequence_is_a_method_of_its_own():
    assert callable(StateMachine._perform_transition)


def test_dispatch_performs_the_transition_through_it(monkeypatch):
    """A real delegation, not a method added alongside the old body: with the
    step replaced by one that does nothing, a dispatched event must leave the
    machine where it was."""
    seen = []
    monkeypatch.setattr(
        StateMachine,
        "_perform_transition",
        lambda self, transition, event, leaf_state_before: seen.append(
            (transition["to_state"], event.name, leaf_state_before)
        ),
    )
    fixture = machine()

    fixture.root.dispatch(Event("pause"))

    assert seen == [(fixture.idle, "pause", fixture.typing)]
    assert fixture.root.leaf_state is fixture.typing


def test_dispatch_is_left_with_the_deciding_half():
    """The states are walked by the extracted step now, so `dispatch` itself
    only decides whether a transition fires at all."""
    source = inspect.getsource(StateMachine.dispatch)

    assert "_exit_states" not in source
    assert "_enter_states" not in source


def test_an_event_with_no_transition_never_reaches_the_step(monkeypatch):
    """The lookup stays on the deciding side: nothing to perform means the
    performing half is not called."""
    seen = []
    monkeypatch.setattr(
        StateMachine,
        "_perform_transition",
        lambda self, transition, event, leaf_state_before: seen.append(event.name),
    )
    fixture = machine()

    fixture.root.dispatch(Event("nothing-handles-this"))

    assert seen == []
