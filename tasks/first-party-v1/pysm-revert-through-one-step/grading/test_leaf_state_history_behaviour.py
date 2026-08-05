"""Behaviour half of the grading suite: what the two history methods do to the
machine and to leaf_state_stack, pinned entry by entry.

The stack contents are the point. Both methods move the machine the same way,
so where they differ is only visible in what is left on the history
afterwards — set_previous_leaf_state adds the state it came from, and
revert_to_previous_leaf_state ends up shorter by one, which is what lets it be
called again and again to walk further back. Everything here passes on the
pristine repository.
"""

import itertools
from typing import NamedTuple

from pysm import Event, State, StateMachine


class Fixture(NamedTuple):
    root: StateMachine
    one: State
    two: State
    three: State
    four: State


def machine():
    """A flat machine of four states, each reachable from the one before, and
    each able to step back on request."""
    root = StateMachine("root")
    states = [State(name) for name in ("one", "two", "three", "four")]
    root.add_state(states[0], initial=True)
    for state in states[1:]:
        root.add_state(state)
    for held, following in itertools.pairwise(states):
        root.add_transition(held, following, events=["next"])
    root.initialize()
    return Fixture(root, *states)


def history(root):
    return [state.name for state in root.leaf_state_stack.deque]


def test_reverting_walks_back_one_state_at_a_time():
    fixture = machine()
    for _ in range(3):
        fixture.root.dispatch(Event("next"))
    assert fixture.root.leaf_state is fixture.four
    assert history(fixture.root) == ["one", "two", "three"]

    fixture.root.revert_to_previous_leaf_state()
    assert fixture.root.leaf_state is fixture.three
    assert history(fixture.root) == ["one", "two"]

    fixture.root.revert_to_previous_leaf_state()
    assert fixture.root.leaf_state is fixture.two
    assert history(fixture.root) == ["one"]

    fixture.root.revert_to_previous_leaf_state()
    assert fixture.root.leaf_state is fixture.one
    assert history(fixture.root) == []


def test_reverting_with_nothing_behind_changes_nothing():
    fixture = machine()

    fixture.root.revert_to_previous_leaf_state()

    assert fixture.root.leaf_state is fixture.one
    assert history(fixture.root) == []


def test_reverting_past_the_start_stays_at_the_start():
    fixture = machine()
    fixture.root.dispatch(Event("next"))

    fixture.root.revert_to_previous_leaf_state()
    fixture.root.revert_to_previous_leaf_state()

    assert fixture.root.leaf_state is fixture.one
    assert history(fixture.root) == []


def test_setting_the_previous_leaf_state_keeps_the_state_it_came_from():
    """The other method: it moves the same way and records the move, so
    calling it twice bounces between two states rather than walking back."""
    fixture = machine()
    fixture.root.dispatch(Event("next"))
    fixture.root.dispatch(Event("next"))
    assert fixture.root.leaf_state is fixture.three
    assert history(fixture.root) == ["one", "two"]

    fixture.root.set_previous_leaf_state()
    assert fixture.root.leaf_state is fixture.two
    assert history(fixture.root) == ["one", "two", "three"]

    fixture.root.set_previous_leaf_state()
    assert fixture.root.leaf_state is fixture.three
    assert history(fixture.root) == ["one", "two", "three", "two"]


def test_setting_the_previous_leaf_state_with_nothing_behind_changes_nothing():
    fixture = machine()

    fixture.root.set_previous_leaf_state()

    assert fixture.root.leaf_state is fixture.one
    assert history(fixture.root) == []


def test_both_methods_fire_the_exit_and_enter_handlers_of_the_move():
    fixture = machine()
    seen = []
    for state in fixture[1:]:
        state.handlers = {
            "exit": lambda held, event, name=state.name: seen.append(("exit", name)),
            "enter": lambda held, event, name=state.name: seen.append(("enter", name)),
        }
    fixture.root.dispatch(Event("next"))
    del seen[:]

    fixture.root.revert_to_previous_leaf_state()
    assert seen == [("exit", "two"), ("enter", "one")]

    del seen[:]
    fixture.root.set_previous_leaf_state()
    assert seen == []


def test_an_event_passed_in_reaches_the_handlers_of_the_move():
    fixture = machine()
    seen = []
    fixture.one.handlers = {
        "enter": lambda held, event: seen.append(event.cargo["source_event"])
    }
    fixture.root.dispatch(Event("next"))
    reason = Event("undo")

    fixture.root.revert_to_previous_leaf_state(reason)

    assert seen == [reason]
    assert reason.state_machine is fixture.root
