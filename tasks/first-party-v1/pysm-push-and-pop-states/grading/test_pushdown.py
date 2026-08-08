"""Held-out tests for StateMachine.push_state and StateMachine.pop_state.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.
"""

import pytest
from pysm import Event, State, StateMachine, StateMachineException


def build(seen=None):
    """root(idle*, work(a*, b), helpdesk), every state reporting its handlers.

    `helpdesk` is the interruption a pushdown machine exists for: somewhere to
    go from anywhere and come back from to wherever you were. `work` is a
    machine so that pushing onto a composite state has something to descend
    into.
    """
    root = StateMachine('root')
    idle = State('idle')
    work = StateMachine('work')
    a = State('a')
    b = State('b')
    helpdesk = State('helpdesk')
    work.add_state(a, initial=True)
    work.add_state(b)
    root.add_state(idle, initial=True)
    root.add_state(work)
    root.add_state(helpdesk)
    if seen is not None:
        for state in (idle, work, a, b, helpdesk):
            state.handlers = {
                'enter': lambda state, event: seen.append(
                    ('enter', state.name, root.leaf_state.name,
                     event.cargo.get('source_event'))),
                'exit': lambda state, event: seen.append(
                    ('exit', state.name, root.leaf_state.name,
                     event.cargo.get('source_event'))),
            }
    root.add_transition(idle, work, events=['go'])
    root.add_transition(work, helpdesk, events=['ask'])
    work.add_transition(a, b, events=['next'])
    root.initialize()
    return root, {
        'idle': idle, 'work': work, 'a': a, 'b': b, 'helpdesk': helpdesk,
    }


def into_b(root):
    root.dispatch(Event('go'))
    root.dispatch(Event('next'))


def test_pushing_moves_to_the_target_and_popping_comes_back():
    root, states = build()
    into_b(root)

    root.push_state(states['helpdesk'])
    assert root.leaf_state is states['helpdesk']

    root.pop_state()
    assert root.leaf_state is states['b']


def test_the_stack_is_unwound_in_the_order_it_was_wound():
    root, states = build()
    into_b(root)

    root.push_state(states['helpdesk'])
    root.push_state(states['idle'])

    assert root.pop_state() is states['helpdesk']
    assert root.leaf_state is states['helpdesk']
    assert root.pop_state() is states['b']
    assert root.leaf_state is states['b']


def test_popping_an_empty_stack_returns_nothing_and_moves_nothing():
    seen = []
    root, states = build(seen)
    into_b(root)
    del seen[:]

    assert root.pop_state() is None

    assert root.leaf_state is states['b']
    assert seen == []


def test_the_state_being_left_is_what_goes_onto_the_stack():
    """Not the state being moved to, which is the slip a stack of two entries
    never shows."""
    root, states = build()
    into_b(root)

    root.push_state(states['helpdesk'])

    assert root.stack.peek() is states['b']


def test_pushing_and_popping_run_the_handlers_a_transition_would_run():
    seen = []
    root, states = build(seen)
    into_b(root)
    del seen[:]

    root.push_state(states['helpdesk'])
    root.pop_state()

    assert [(kind, name, leaf) for kind, name, leaf, _ in seen] == [
        ('exit', 'b', 'b'),
        ('exit', 'work', 'work'),
        ('enter', 'helpdesk', 'helpdesk'),
        ('exit', 'helpdesk', 'helpdesk'),
        ('enter', 'work', 'work'),
        ('enter', 'b', 'b'),
    ]


def test_pushing_onto_a_machine_descends_to_the_substate_it_is_on():
    root, states = build()
    root.push_state(states['work'])

    assert root.leaf_state is states['a']

    root.pop_state()
    assert root.leaf_state is states['idle']


def test_the_history_stacks_get_what_an_ordinary_transition_puts_there():
    """The rule the prompt states, read against the thing it names.

    Two machines built the same way are taken from `work` to `helpdesk`, one
    by dispatching the transition that goes there and one by pushing, and the
    stacks of historical states are compared afterwards. Whatever a dispatch
    records, a push records.
    """
    dispatched, _ = build()
    pushed, states = build()
    into_b(dispatched)
    into_b(pushed)

    dispatched.dispatch(Event('ask'))
    pushed.push_state(states['helpdesk'])

    def history(machine):
        inner = [state for state in machine.states
                 if isinstance(state, StateMachine)]
        return (
            [state.name for state in machine.leaf_state_stack.deque],
            [state.name for state in machine.state_stack.deque],
            sorted((child.name,
                    [state.name for state in child.state_stack.deque])
                   for child in inner),
        )

    assert history(pushed) == history(dispatched)


def test_the_event_reaches_the_handlers_as_the_source_event():
    seen = []
    root, states = build(seen)
    into_b(root)
    del seen[:]
    asked = Event('asked')
    answered = Event('answered')

    root.push_state(states['helpdesk'], asked)
    root.pop_state(answered)

    assert [source for _, _, _, source in seen] == [
        asked, asked, asked, answered, answered, answered,
    ]
    assert asked.state_machine is root
    assert answered.state_machine is root


def test_pushing_from_a_machine_that_was_never_initialized_is_refused():
    root = StateMachine('root')
    only = State('only')
    other = State('other')
    root.add_state(only, initial=True)
    root.add_state(other)

    with pytest.raises(StateMachineException):
        root.push_state(other)
