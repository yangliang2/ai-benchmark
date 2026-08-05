"""Behaviour half of the grading suite: what a dispatched event does, pinned
so that lifting the transition sequence out of `dispatch` cannot change it.

The part that matters most here is which state each transition callback is
handed, because that is the part the repository's own tests no longer look at:
`before` and `action` see the leaf state the machine is leaving, and `after`
sees the one it has arrived at. Everything in this file passes on the pristine
repository and has to go on passing afterwards.
"""

from typing import NamedTuple

from pysm import Event, State, StateMachine


class Fixture(NamedTuple):
    root: StateMachine
    work: StateMachine
    typing: State
    idle: State
    away: State


def machine():
    """A two-level machine: root -> work -> {typing, idle}, plus a top-level
    away state, so a transition can cross one level or two."""
    root = StateMachine("root")
    work = StateMachine("work")
    typing, idle, away = State("typing"), State("idle"), State("away")
    work.add_state(typing, initial=True)
    work.add_state(idle)
    root.add_state(work, initial=True)
    root.add_state(away)
    return Fixture(root, work, typing, idle, away)


def test_the_callbacks_run_in_the_documented_order():
    fixture = machine()
    seen = []

    def note(label):
        def callback(state, event):
            seen.append((label, state.name))
            return True

        return callback

    fixture.typing.handlers = {"pause": note("handler"), "exit": note("exit")}
    fixture.idle.handlers = {"enter": note("enter")}
    fixture.work.add_transition(
        fixture.typing, fixture.idle, events=["pause"],
        condition=note("condition"), before=note("before"),
        action=note("action"), after=note("after"),
    )
    fixture.root.initialize()

    fixture.root.dispatch(Event("pause"))

    assert [label for label, _ in seen] == [
        "handler", "condition", "before", "exit", "action", "enter", "after"
    ]


def test_before_and_action_see_the_state_being_left():
    fixture = machine()
    seen = {}
    fixture.work.add_transition(
        fixture.typing, fixture.idle, events=["pause"],
        before=lambda state, event: seen.setdefault("before", state),
        action=lambda state, event: seen.setdefault("action", state),
    )
    fixture.root.initialize()

    fixture.root.dispatch(Event("pause"))

    assert seen == {"before": fixture.typing, "action": fixture.typing}


def test_after_sees_the_state_that_has_been_entered():
    """The one asymmetry in the sequence: `after` runs once the machine has
    arrived, so it is handed the state it arrived at, not the one it left."""
    fixture = machine()
    seen = {}

    def after(state, event):
        seen["state"] = state
        seen["leaf_state"] = fixture.root.leaf_state

    fixture.work.add_transition(
        fixture.typing, fixture.idle, events=["pause"], after=after
    )
    fixture.root.initialize()

    fixture.root.dispatch(Event("pause"))

    assert seen == {"state": fixture.idle, "leaf_state": fixture.idle}


def test_exiting_two_levels_does_not_change_what_the_callbacks_see():
    """Where `action` parts company with the machine's current leaf state.
    `action` runs after the exit walk, and on a transition that leaves a
    composite state that walk has already climbed past the leaf — so the leaf
    state by then is the outermost state exited, while `action` is still owed
    the one the transition started from, exactly as on a single-level exit.
    """
    fixture = machine()
    seen = {}
    fixture.root.add_transition(
        fixture.work, fixture.away, events=["leave"],
        before=lambda state, event: seen.setdefault("before", state),
        action=lambda state, event: seen.setdefault("action", state),
        after=lambda state, event: seen.setdefault("after", state),
    )
    fixture.root.initialize()

    fixture.root.dispatch(Event("leave"))

    assert seen == {
        "before": fixture.typing, "action": fixture.typing, "after": fixture.away
    }


def test_after_sees_the_leaf_when_the_target_is_a_composite_state():
    """The target of a transition need not be the state the machine ends up
    in: naming a composite state means the entry path keeps descending to its
    substate, and `after` runs at the end of that descent. So what it is
    handed is the leaf arrived at, not the state the transition names.
    """
    fixture = machine()
    seen = {}
    fixture.root.add_transition(fixture.work, fixture.away, events=["leave"])
    fixture.root.add_transition(
        fixture.away, fixture.work, events=["back"],
        after=lambda state, event: seen.setdefault("after", state),
    )
    fixture.root.initialize()

    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))

    assert seen == {"after": fixture.typing}
    assert fixture.root.leaf_state is fixture.typing


def test_exit_and_entry_handlers_walk_the_hierarchy():
    fixture = machine()
    seen = []
    for state in fixture:
        state.handlers = {
            "exit": lambda held, event, name=state.name: seen.append(("exit", name)),
            "enter": lambda held, event, name=state.name: seen.append(("enter", name)),
        }
    fixture.root.add_transition(fixture.work, fixture.away, events=["leave"])
    fixture.root.add_transition(fixture.away, fixture.work, events=["back"])
    fixture.root.initialize()

    fixture.root.dispatch(Event("leave"))
    fixture.root.dispatch(Event("back"))

    assert seen == [
        ("exit", "typing"), ("exit", "work"), ("enter", "away"),
        ("exit", "away"), ("enter", "work"), ("enter", "typing"),
    ]


def test_leaf_state_and_the_history_stack_agree_after_a_transition():
    fixture = machine()
    fixture.work.add_transition(fixture.typing, fixture.idle, events=["pause"])
    fixture.root.add_transition(fixture.work, fixture.away, events=["leave"])
    fixture.root.initialize()

    assert fixture.root.leaf_state is fixture.typing
    fixture.root.dispatch(Event("pause"))
    assert fixture.root.leaf_state is fixture.idle
    assert list(fixture.root.leaf_state_stack.deque) == [fixture.typing]
    fixture.root.dispatch(Event("leave"))
    assert fixture.root.leaf_state is fixture.away
    assert list(fixture.root.leaf_state_stack.deque) == [fixture.typing, fixture.idle]

    fixture.root.revert_to_previous_leaf_state()

    assert fixture.root.leaf_state is fixture.idle
    assert list(fixture.root.leaf_state_stack.deque) == [fixture.typing]


def test_an_event_with_no_transition_still_reaches_the_state_handler():
    fixture = machine()
    seen = []
    fixture.typing.handlers = {"tick": lambda state, event: seen.append(state)}
    fixture.root.initialize()

    fixture.root.dispatch(Event("tick"))

    assert seen == [fixture.typing]
    assert fixture.root.leaf_state is fixture.typing
