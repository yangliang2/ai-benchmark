"""Held-out tests for StateMachine.trace.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.

The suite is built around one idea the prompt states outright — the same graph
driven the same way records the same trace whichever execution layer is
running it. That is what makes a recording site missed in one layer visible
here rather than only in a layer nobody exercised.

And around a second the prompt states just as plainly, which these tests did
not check until #42's final pass: the trace belongs to the root machine. Every
site records on the machine the call was made on, so a suite that only ever
drives the graph from its root writes `self.trace` and
`self.root_machine.trace` into one list and cannot tell them apart. The cases
that dispatch to and initialize a nested machine are here for that, one per
layer.
"""

import asyncio

import pytest
from pysm import Event, State, StateMachine, StateMachineException
from pysm.aio import AsyncQueuedStateMachine
from pysm.queued import QueuedStateMachine, ThreadSafeQueuedStateMachine
from pysm.serialization import snapshot


def graph(cls=StateMachine, inner_cls=StateMachine):
    """root(idle*, work(a*, b)) — a machine inside a machine, so that entering
    `work` is two entries deep and leaving it is two exits.

    The nested machine's class is chosen separately from the root's, so that a
    queued or an async layer can sit underneath the root as well as at it. That
    is what lets a call be made on a machine that is not the root in every
    layer, which is the only circumstance in which `self` and
    `self.root_machine` are different objects.
    """
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


def test_a_nested_machine_initialized_on_its_own_records_on_the_root():
    """The initial walk, asked of a machine that is not the root — the first
    of the cases here to separate `self` from `self.root_machine`.

    `initialize` may be called on any machine in the graph. Drive the graph
    from the root, as every case above does, and the two names are one list,
    so a solution that wrote `self.trace` in the initial-path walk instead of
    `self.root_machine.trace` recorded into the right place everywhere they
    look. Here it does not: the entries belong to the root, and the nested
    machine's own trace stays empty, which is what the prompt asks for in as
    many words. `dispatch` can be called below the root too, and the cases
    that follow ask the same of it in each of the three modules.
    """
    root, states = graph()
    root.initialize()

    states['work'].initialize(fire_events_on_init=True)

    assert list(root.trace) == [('enter', 'a')]
    assert list(states['work'].trace) == []


def test_dispatching_to_a_nested_machine_records_on_the_root():
    """`initialize` is not the only call that can be made below the root, and
    the rest of them are where the same slip hides.

    Everything `dispatch` records — the event arriving, the states left, the
    states entered, and the deferral the queued layer makes when a handler
    dispatches into a machine that is already running one — is written by the
    machine the call was made on. Drive the graph from the root and that
    machine *is* the root, so `self.trace` and `self.root_machine.trace` name
    one list and nothing separates them. Dispatch to the nested machine and
    they come apart: the entries still belong to the root, and `work`'s own
    trace stays empty, which is what the prompt asks for in as many words.
    """
    root, states = graph(inner_cls=QueuedStateMachine)
    inner = states['work']
    root.initialize()
    root.dispatch(Event('go'))
    states['b'].handlers = {'enter': lambda state, event: inner.dispatch(
        Event('spin'))}

    inner.dispatch(Event('next'))

    assert list(root.trace) == [
        ('event', 'go'),
        ('exit', 'idle'),
        ('enter', 'work'),
        ('enter', 'a'),
        ('event', 'next'),
        ('exit', 'a'),
        ('enter', 'b'),
        ('queued', 'spin'),
        ('event', 'spin'),
    ]
    assert list(inner.trace) == []


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


def test_a_nested_async_machine_initialized_on_its_own_records_on_the_root():
    """The async layer's copy of the initial walk, asked the question the
    core's copy is asked above. The two walks are written out separately —
    that is the whole reason this task is wide — so an answer can get the rule
    right in one of them and wrong in the other, and nothing that drives the
    async layer from its root would say so."""
    async def scenario():
        root, states = graph(AsyncQueuedStateMachine, AsyncQueuedStateMachine)
        root.initialize()

        await states['work'].async_initialize(fire_events_on_init=True)

        return list(root.trace), list(states['work'].trace)

    assert asyncio.run(scenario()) == ([('enter', 'a')], [])


def test_dispatching_to_a_nested_async_machine_records_on_the_root():
    """And the async layer's copies of the dispatching step and of the two
    walks it drives, asked the same question as the core's."""
    async def scenario():
        root, states = graph(AsyncQueuedStateMachine, AsyncQueuedStateMachine)
        inner = states['work']
        root.initialize()
        await root.dispatch(Event('go'))

        async def defer(state, event):
            await inner.dispatch(Event('spin'))

        states['b'].handlers = {'enter': defer}
        await inner.dispatch(Event('next'))
        return list(root.trace), list(inner.trace)

    assert asyncio.run(scenario()) == ([
        ('event', 'go'),
        ('exit', 'idle'),
        ('enter', 'work'),
        ('enter', 'a'),
        ('event', 'next'),
        ('exit', 'a'),
        ('enter', 'b'),
        ('queued', 'spin'),
        ('event', 'spin'),
    ], [])


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


def test_what_a_nested_machine_throws_away_is_recorded_on_the_root():
    """The last of the queued layer's recordings put to the nested machine,
    since a machine below the root clears its own queues when a handler under
    it fails."""
    root, states = graph(inner_cls=QueuedStateMachine)
    inner = states['work']
    root.initialize()
    root.dispatch(Event('go'))

    def blow_up(state, event):
        inner.dispatch(Event('spin'))
        raise Boom()

    states['b'].handlers = {'enter': blow_up}

    with pytest.raises(Boom):
        inner.dispatch(Event('next'))

    assert list(root.trace)[-2:] == [('queued', 'spin'), ('dropped', 'spin')]
    assert list(inner.trace) == []


def test_what_a_nested_async_machine_throws_away_is_recorded_on_the_root():
    """And the async layer's own copy of that clearing, which is a fourth
    place the same rule has to be written and a fourth place it can be
    written wrong."""
    async def scenario():
        root, states = graph(AsyncQueuedStateMachine, AsyncQueuedStateMachine)
        inner = states['work']
        root.initialize()
        await root.dispatch(Event('go'))

        async def blow_up(state, event):
            await inner.dispatch(Event('spin'))
            raise Boom()

        states['b'].handlers = {'enter': blow_up}
        with pytest.raises(Boom):
            await inner.dispatch(Event('next'))
        return list(root.trace), list(inner.trace)

    assert asyncio.run(scenario()) == ([
        ('event', 'go'),
        ('exit', 'idle'),
        ('enter', 'work'),
        ('enter', 'a'),
        ('event', 'next'),
        ('exit', 'a'),
        ('enter', 'b'),
        ('queued', 'spin'),
        ('dropped', 'spin'),
    ], [])


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
