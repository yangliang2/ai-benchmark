"""Held-out tests for StateMachine.trace.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.

The suite is built around one idea the prompt states outright — the same graph
driven the same way records the same trace whichever execution layer is
running it. That is what makes a recording site missed in one layer visible
here rather than only in a layer nobody exercised.
"""

import asyncio

import pytest
from pysm import Event, State, StateMachine, StateMachineException
from pysm.aio import AsyncQueuedStateMachine
from pysm.queued import QueuedStateMachine, ThreadSafeQueuedStateMachine
from pysm.serialization import snapshot


def graph(cls=StateMachine):
    """root(idle*, work(a*, b)) — a machine inside a machine, so that entering
    `work` is two entries deep and leaving it is two exits."""
    root = cls('root')
    idle = State('idle')
    work = StateMachine('work')
    a = State('a')
    b = State('b')
    work.add_state(a, initial=True)
    work.add_state(b)
    root.add_state(idle, initial=True)
    root.add_state(work)
    root.add_transition(idle, work, events=['go'])
    root.add_transition(work, idle, events=['stop'])
    work.add_transition(a, b, events=['next'])
    return root, {'idle': idle, 'work': work, 'a': a, 'b': b}


def test_a_machine_that_has_done_nothing_has_recorded_nothing():
    root, _ = graph()

    assert list(root.trace) == []

    root.initialize()

    assert list(root.trace) == []


def test_firing_the_initial_states_records_the_path_that_was_entered():
    root, _ = graph()

    root.initialize(fire_events_on_init=True)

    assert list(root.trace) == [('enter', 'idle')]


def test_a_transition_records_the_event_then_what_it_left_and_entered():
    root, _ = graph()
    root.initialize()

    root.dispatch(Event('go'))

    assert list(root.trace) == [
        ('event', 'go'),
        ('exit', 'idle'),
        ('enter', 'work'),
        ('enter', 'a'),
    ]


def test_an_event_that_moves_nothing_is_still_recorded():
    root, _ = graph()
    root.initialize()

    root.dispatch(Event('unknown'))

    assert list(root.trace) == [('event', 'unknown')]


def test_an_event_refused_before_initialize_records_nothing():
    root, _ = graph()

    with pytest.raises(StateMachineException):
        root.dispatch(Event('go'))

    assert list(root.trace) == []


def test_only_the_root_machine_records():
    """The trace goes where `leaf_state` goes. A nested machine has one and
    never writes to it, so a reader of the root gets the whole story in one
    place and in one order."""
    root, states = graph()
    root.initialize(fire_events_on_init=True)
    root.dispatch(Event('go'))
    root.dispatch(Event('next'))

    assert list(states['work'].trace) == []
    assert len(root.trace) > 1


def test_the_recording_keeps_going_across_several_events():
    root, _ = graph()
    root.initialize()

    root.dispatch(Event('go'))
    root.dispatch(Event('next'))
    root.dispatch(Event('stop'))

    assert list(root.trace) == [
        ('event', 'go'),
        ('exit', 'idle'),
        ('enter', 'work'),
        ('enter', 'a'),
        ('event', 'next'),
        ('exit', 'a'),
        ('enter', 'b'),
        ('event', 'stop'),
        ('exit', 'b'),
        ('exit', 'work'),
        ('enter', 'idle'),
    ]


def drive(root):
    """Take a machine from idle to work and on to b, synchronously."""
    root.initialize()
    root.dispatch(Event('go'))
    root.dispatch(Event('next'))
    return list(root.trace)


def test_the_queued_layer_records_what_the_core_records():
    plain, _ = graph(StateMachine)
    queued, _ = graph(QueuedStateMachine)

    assert drive(queued) == drive(plain)
    assert len(plain.trace) == 7


def test_the_thread_safe_queued_layer_records_what_the_core_records():
    plain, _ = graph(StateMachine)
    guarded, _ = graph(ThreadSafeQueuedStateMachine)

    assert drive(guarded) == drive(plain)
    assert len(plain.trace) == 7


def test_the_async_layer_records_what_the_core_records():
    """The one that costs a reader of only `pysm/pysm.py` the task: the async
    layer has its own copies of the entry walk, the exit walk and the
    dispatching step, and none of them inherits from the core's."""
    plain, _ = graph(StateMachine)
    expected = drive(plain)

    async def scenario():
        machine, _ = graph(AsyncQueuedStateMachine)
        machine.initialize()
        await machine.dispatch(Event('go'))
        await machine.dispatch(Event('next'))
        return list(machine.trace)

    assert asyncio.run(scenario()) == expected
    assert len(expected) == 7


def test_the_async_layer_records_the_initial_path_it_enters():
    async def scenario():
        machine, _ = graph(AsyncQueuedStateMachine)
        await machine.async_initialize(fire_events_on_init=True)
        return list(machine.trace)

    assert asyncio.run(scenario()) == [('enter', 'idle')]


def test_an_event_a_handler_dispatches_is_recorded_as_queued_then_handled():
    """A handler dispatching while the machine is already running does not get
    handled there and then; the queued layer defers it. Both moments are
    recorded, in the order they happened."""
    root, states = graph(QueuedStateMachine)
    states['a'].handlers = {'enter': lambda state, event: root.dispatch(
        Event('next'))}
    root.initialize()

    root.dispatch(Event('go'))

    assert list(root.trace) == [
        ('event', 'go'),
        ('exit', 'idle'),
        ('enter', 'work'),
        ('enter', 'a'),
        ('queued', 'next'),
        ('event', 'next'),
        ('exit', 'a'),
        ('enter', 'b'),
    ]


def test_the_async_layer_records_a_deferred_event_the_same_way():
    async def scenario():
        machine, states = graph(AsyncQueuedStateMachine)

        async def defer(state, event):
            await machine.dispatch(Event('next'))

        states['a'].handlers = {'enter': defer}
        machine.initialize()
        await machine.dispatch(Event('go'))
        return list(machine.trace)

    assert asyncio.run(scenario()) == [
        ('event', 'go'),
        ('exit', 'idle'),
        ('enter', 'work'),
        ('enter', 'a'),
        ('queued', 'next'),
        ('event', 'next'),
        ('exit', 'a'),
        ('enter', 'b'),
    ]


class Boom(Exception):
    pass


def test_events_thrown_away_after_a_failure_are_recorded_as_dropped():
    root, states = graph(QueuedStateMachine)

    def blow_up(state, event):
        root.dispatch(Event('first'))
        root.dispatch(Event('second'))
        raise Boom()

    states['a'].handlers = {'enter': blow_up}
    root.initialize()

    with pytest.raises(Boom):
        root.dispatch(Event('go'))

    assert list(root.trace)[-4:] == [
        ('queued', 'first'),
        ('queued', 'second'),
        ('dropped', 'first'),
        ('dropped', 'second'),
    ]


def test_the_async_layer_records_what_it_throws_away_too():
    async def scenario():
        machine, states = graph(AsyncQueuedStateMachine)

        async def blow_up(state, event):
            await machine.dispatch(Event('first'))
            raise Boom()

        states['a'].handlers = {'enter': blow_up}
        machine.initialize()
        with pytest.raises(Boom):
            await machine.dispatch(Event('go'))
        return list(machine.trace)

    assert asyncio.run(scenario())[-2:] == [
        ('queued', 'first'),
        ('dropped', 'first'),
    ]


def test_the_trace_is_the_machine_s_own_and_two_machines_do_not_share_one():
    one, _ = graph()
    other, _ = graph()
    one.initialize()
    other.initialize()

    one.dispatch(Event('go'))

    assert list(other.trace) == []
    assert len(one.trace) == 4


def test_recording_does_not_reach_the_parts_of_the_machine_others_read():
    """Nothing else about the library moves: the states, the history stacks
    and what a snapshot holds are what they were."""
    traced, _ = graph()
    traced.initialize()
    traced.dispatch(Event('go'))

    assert traced.leaf_state.name == 'a'
    assert [state.name for state in traced.leaf_state_stack.deque] == ['idle']
    assert snapshot(traced)['leaf_state'] == ['root', 'work', 'a']
    assert ('enter', 'a') in traced.trace
