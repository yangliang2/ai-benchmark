"""Held-out tests for refusing a snapshot or a restore taken mid-flight.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.

Two halves, and both matter. A machine that is part-way through handling an
event is refused, whichever of the package's execution layers is running it
and wherever in the graph it sits; a machine that is standing still is not
refused, so the guard cannot be a blanket one.
"""

import asyncio

import pytest
from pysm import Event, State, StateMachine, StateMachineException
from pysm.aio import AsyncQueuedStateMachine
from pysm.queued import QueuedStateMachine, ThreadSafeQueuedStateMachine
from pysm.serialization import restore, snapshot


def graph(cls=StateMachine, inner_cls=StateMachine):
    """root(idle*, work(a*, b)), with the class of each machine chosen so a
    queued layer can sit at the root or nested underneath a plain one."""
    root = cls('root')
    idle = State('idle')
    work = inner_cls('work')
    a = State('a')
    b = State('b')
    work.add_state(a, initial=True)
    work.add_state(b)
    root.add_state(idle, initial=True)
    root.add_state(work)
    root.add_transition(idle, work, events=['go'])
    work.add_transition(a, b, events=['next'])
    root.initialize()
    return root, {'idle': idle, 'work': work, 'a': a, 'b': b}


def attempt(machine, data):
    """What snapshot and restore do here, as words rather than exceptions."""
    outcome = []
    for call in (lambda: snapshot(machine), lambda: restore(machine, data)):
        try:
            call()
            outcome.append('allowed')
        except StateMachineException:
            outcome.append('refused')
    return outcome


# --- a machine standing still is not refused ------------------------------------


def test_a_core_machine_is_snapshotted_and_restored_as_before():
    root, states = graph()
    data = snapshot(root)

    root.dispatch(Event('go'))
    assert root.leaf_state is states['a']

    restore(root, data)

    assert root.leaf_state is states['idle']


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine,
                                 AsyncQueuedStateMachine])
def test_a_queued_machine_that_is_not_running_is_not_refused(cls):
    """The guard reads whether the machine is busy, not what class it is."""
    root, _ = graph(cls)

    assert attempt(root, snapshot(root)) == ['allowed', 'allowed']


def test_a_machine_is_not_refused_once_the_cycle_it_ran_is_over():
    root, states = graph(QueuedStateMachine)
    root.dispatch(Event('go'))

    assert attempt(root, snapshot(root)) == ['allowed', 'allowed']
    assert root.leaf_state is states['a']


# --- a machine part-way through an event is refused -----------------------------


def during(root, states, look):
    """Run `go` and let `look` try something while `a` is being entered."""
    seen = []
    states['a'].handlers = {'enter': lambda state, event: seen.append(
        look(root))}
    root.dispatch(Event('go'))
    return seen


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_a_queued_machine_handling_an_event_refuses_both(cls):
    root, states = graph(cls)
    data = snapshot(root)

    assert during(root, states, lambda machine: attempt(machine, data)) == [
        ['refused', 'refused']]


def test_an_async_machine_handling_an_event_refuses_both():
    """The async layer does not inherit from the queued one, so a guard that
    asks what class the machine is rather than what it is doing lets this
    one through."""
    async def scenario():
        root, states = graph(AsyncQueuedStateMachine)
        data = snapshot(root)
        seen = []

        async def on_enter(state, event):
            seen.append(attempt(root, data))

        states['a'].handlers = {'enter': on_enter}
        await root.dispatch(Event('go'))
        return seen

    assert asyncio.run(scenario()) == [['refused', 'refused']]


def test_a_queued_machine_nested_under_a_plain_root_is_found():
    """The whole graph is asked, not the machine the call was made on: the
    busy machine here is a child, and the root that is being snapshotted is
    an ordinary core machine that is never busy."""
    root, states = graph(StateMachine, QueuedStateMachine)
    data = snapshot(root)
    root.dispatch(Event('go'))
    inner = states['work']

    seen = []
    states['b'].handlers = {'enter': lambda state, event: seen.append(
        attempt(root, data))}
    inner.dispatch(Event('next'))

    assert seen == [['refused', 'refused']]


def test_the_call_may_be_made_on_any_machine_in_the_graph():
    """`snapshot` and `restore` already climb to the root before doing
    anything; the refusal climbs with them."""
    root, states = graph(QueuedStateMachine)
    data = snapshot(root)

    assert during(root, states,
                  lambda machine: attempt(states['work'], data)) == [
        ['refused', 'refused']]


def test_a_refused_restore_leaves_the_machine_where_it_was():
    """The reason the refusal is worth having: a restore that went through
    here would move the graph out from under the transition that is still
    walking it."""
    root, states = graph(QueuedStateMachine)
    at_idle = snapshot(root)

    def look(machine):
        try:
            restore(machine, at_idle)
        except StateMachineException:
            return 'refused'
        return 'allowed'

    assert during(root, states, look) == ['refused']
    assert root.leaf_state is states['a']


def test_what_is_refused_is_a_state_machine_exception():
    root, states = graph(QueuedStateMachine)

    def look(machine):
        with pytest.raises(StateMachineException):
            snapshot(machine)
        return 'raised'

    assert during(root, states, look) == ['raised']
