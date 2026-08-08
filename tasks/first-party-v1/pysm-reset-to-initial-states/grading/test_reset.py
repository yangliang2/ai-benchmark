"""Held-out tests for StateMachine.reset.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.
"""

import pytest
from pysm import Event, State, StateMachine, StateMachineException


def build(seen=None):
    """root(idle*, work(a*, b)), every state reporting what it was handed.

    Two levels is the least that separates "put the root back" from "put the
    whole graph back", and the initial state of the root is a plain state
    while the other branch is a machine, so a reset out of `work` has to
    climb before it descends.
    """
    root = StateMachine('root')
    idle = State('idle')
    work = StateMachine('work')
    a = State('a')
    b = State('b')
    work.add_state(a, initial=True)
    work.add_state(b)
    root.add_state(idle, initial=True)
    root.add_state(work)
    if seen is not None:
        # The leaf is read off the machine rather than off the event, so that
        # what is pinned is where the machine says it is while a handler runs
        # and not how the handler was reached.
        for state in (idle, work, a, b):
            state.handlers = {
                'enter': lambda state, event: seen.append(
                    ('enter', state.name, root.leaf_state.name,
                     event.cargo.get('source_event'))),
                'exit': lambda state, event: seen.append(
                    ('exit', state.name, root.leaf_state.name,
                     event.cargo.get('source_event'))),
            }
    root.add_transition(idle, work, events=['go'])
    root.add_transition(work, idle, events=['stop'])
    work.add_transition(a, b, events=['next'])
    root.initialize()
    return root, {'idle': idle, 'work': work, 'a': a, 'b': b}


def into_b(root):
    """Drive the machine to the deepest state it has."""
    root.dispatch(Event('go'))
    root.dispatch(Event('next'))


def test_reset_puts_every_machine_back_on_its_initial_state():
    root, states = build()
    into_b(root)
    assert root.leaf_state is states['b']

    root.reset()

    assert root.leaf_state is states['idle']
    assert root.state is states['idle']
    assert states['work'].state is states['a']


def test_reset_leaves_the_machine_usable():
    """The configuration has to be the real one and not merely reported: the
    same events have to take the machine the same way again."""
    root, states = build()
    into_b(root)

    root.reset()
    into_b(root)

    assert root.leaf_state is states['b']


def test_reset_runs_the_handlers_a_transition_would_run():
    seen = []
    root, _ = build(seen)
    into_b(root)
    del seen[:]

    root.reset()

    assert [(kind, name) for kind, name, _, _ in seen] == [
        ('exit', 'b'), ('exit', 'work'), ('enter', 'idle'),
    ]


def test_each_handler_is_run_with_its_own_state_as_the_leaf():
    """What a handler sees while it runs. `leaf_state` names the state being
    left or entered, exactly as it does during a dispatched transition, so a
    handler asking the machine where it is gets an answer about itself."""
    seen = []
    root, _ = build(seen)
    into_b(root)
    del seen[:]

    root.reset()

    assert [(name, leaf) for _, name, leaf, _ in seen] == [
        ('b', 'b'), ('work', 'work'), ('idle', 'idle'),
    ]


def test_the_event_reaches_the_handlers_as_the_source_event():
    seen = []
    root, _ = build(seen)
    into_b(root)
    del seen[:]
    reboot = Event('reboot')

    root.reset(reboot)

    assert [source for _, _, _, source in seen] == [reboot, reboot, reboot]
    assert reboot.state_machine is root


def test_passing_no_event_leaves_the_source_event_empty():
    seen = []
    root, _ = build(seen)
    into_b(root)
    del seen[:]

    root.reset()

    assert [source for _, _, _, source in seen] == [None, None, None]


def test_reset_records_nothing_on_the_stacks_of_historical_states():
    """The rule the prompt states, and the one an answer built out of the
    machinery a dispatch uses has to go back for: the exit walk a transition
    performs pushes the leaf it left and every state it climbed past."""
    root, states = build()
    into_b(root)
    before = (
        list(root.leaf_state_stack.deque),
        list(root.state_stack.deque),
        list(states['work'].state_stack.deque),
        list(root.stack.deque),
    )

    root.reset()

    assert (
        list(root.leaf_state_stack.deque),
        list(root.state_stack.deque),
        list(states['work'].state_stack.deque),
        list(root.stack.deque),
    ) == before


def test_resetting_from_the_initial_configuration_still_runs_the_handlers():
    """Reset is a move, not a check: a machine sitting where it started is
    left and entered again rather than passed over."""
    seen = []
    root, states = build(seen)

    root.reset()

    assert [(kind, name) for kind, name, _, _ in seen] == [
        ('exit', 'idle'), ('enter', 'idle'),
    ]
    assert root.leaf_state is states['idle']


def test_resetting_a_machine_that_was_never_initialized_is_refused():
    root = StateMachine('root')
    root.add_state(State('only'), initial=True)

    with pytest.raises(StateMachineException):
        root.reset()
