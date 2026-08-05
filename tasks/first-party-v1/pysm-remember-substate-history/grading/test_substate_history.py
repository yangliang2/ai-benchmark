"""Held-out grading suite for shallow history on composite states.

Most of what is checked here is not the new feature but the contracts around
it: which handlers fire and in what order once an entry path resumes part-way
down, that leaf_state still names the state the machine is in, that
state_stack still records what was left, and that a machine without history
behaves exactly as it did. The feature is two lines; these are what the two
lines have to leave standing.
"""

from typing import NamedTuple

from pysm import Event, State, StateMachine


class Fixture(NamedTuple):
    root: StateMachine
    work: StateMachine
    typing: State
    reviewing: State
    away: State


NOT_ASKED_FOR = object()


def machine(history=NOT_ASKED_FOR):
    """root -> {work -> {typing, reviewing}, away}, with work optionally
    remembering which substate it was in. Called with no argument, the keyword
    is not passed at all — the way every machine already in the wild is built.
    """
    root = StateMachine("root")
    work = (
        StateMachine("work")
        if history is NOT_ASKED_FOR
        else StateMachine("work", history=history)
    )
    typing, reviewing, away = State("typing"), State("reviewing"), State("away")
    work.add_state(typing, initial=True)
    work.add_state(reviewing)
    root.add_state(work, initial=True)
    root.add_state(away)
    work.add_transition(typing, reviewing, events=["review"])
    root.add_transition(work, away, events=["leave"])
    root.add_transition(away, work, events=["back"])
    root.initialize()
    return Fixture(root, work, typing, reviewing, away)


def test_a_history_machine_resumes_at_the_substate_it_left():
    fixture = machine(history=True)

    fixture.root.dispatch(Event("review"))
    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))

    assert fixture.root.leaf_state is fixture.reviewing


def test_a_machine_without_history_starts_from_its_initial_substate_again():
    fixture = machine(history=False)

    fixture.root.dispatch(Event("review"))
    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))

    assert fixture.root.leaf_state is fixture.typing


def test_history_is_off_unless_it_is_asked_for():
    """The keyword defaults to off, so every machine in the wild keeps the
    behaviour it has today without being touched: built without asking for
    history, `work` resets to its initial substate on the way out and the
    entry path back in stops at that one, exactly as it does today.
    """
    fixture = machine()
    seen = []
    for state in fixture:
        state.handlers = {
            "enter": lambda held, event, name=state.name: seen.append(name),
        }

    fixture.root.dispatch(Event("review"))
    del seen[:]
    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))

    assert seen == ["away", "work", "typing"]
    assert fixture.root.leaf_state is fixture.typing
    assert fixture.work.state is fixture.typing


def test_a_history_machine_not_yet_entered_starts_at_its_initial_state():
    fixture = machine(history=True)

    assert fixture.root.leaf_state is fixture.typing


def test_a_history_machine_resumes_again_and_again():
    fixture = machine(history=True)

    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))
    assert fixture.root.leaf_state is fixture.typing

    fixture.root.dispatch(Event("review"))
    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))
    assert fixture.root.leaf_state is fixture.reviewing

    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))
    assert fixture.root.leaf_state is fixture.reviewing


def test_the_entry_path_fires_handlers_down_to_the_resumed_substate():
    fixture = machine(history=True)
    seen = []
    for state in fixture:
        state.handlers = {
            "exit": lambda held, event, name=state.name: seen.append(("exit", name)),
            "enter": lambda held, event, name=state.name: seen.append(("enter", name)),
        }

    fixture.root.dispatch(Event("review"))
    del seen[:]
    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))

    assert seen == [
        ("exit", "reviewing"), ("exit", "work"), ("enter", "away"),
        ("exit", "away"), ("enter", "work"), ("enter", "reviewing"),
    ]


def test_leaf_state_agrees_with_the_resumed_substate_at_every_step():
    fixture = machine(history=True)
    seen = []
    for state in (fixture.work, fixture.reviewing):
        state.handlers = {
            "enter": lambda held, event: seen.append(
                (held, fixture.root.leaf_state)
            ),
        }

    fixture.root.dispatch(Event("review"))
    fixture.root.dispatch(Event("leave"))
    del seen[:]
    fixture.root.dispatch(Event("back"))

    assert seen == [
        (fixture.work, fixture.work), (fixture.reviewing, fixture.reviewing)
    ]
    assert fixture.work.state is fixture.reviewing


def test_the_state_stack_still_records_what_was_left():
    fixture = machine(history=True)

    fixture.root.dispatch(Event("review"))
    fixture.root.dispatch(Event("leave"))

    assert list(fixture.work.state_stack.deque) == [fixture.typing, fixture.reviewing]
    assert list(fixture.root.state_stack.deque) == [fixture.work]
    assert list(fixture.root.leaf_state_stack.deque) == [
        fixture.typing, fixture.reviewing
    ]


def test_reverting_to_the_previous_leaf_state_crosses_a_history_machine():
    fixture = machine(history=True)

    fixture.root.dispatch(Event("review"))
    fixture.root.dispatch(Event("leave"))
    assert fixture.root.leaf_state is fixture.away

    fixture.root.revert_to_previous_leaf_state()

    assert fixture.root.leaf_state is fixture.reviewing
    assert list(fixture.root.leaf_state_stack.deque) == [fixture.typing]
