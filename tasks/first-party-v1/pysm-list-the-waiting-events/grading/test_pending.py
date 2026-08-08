"""Held-out tests for QueuedStateMachine.pending and .drop_pending.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.
"""

import asyncio

import pytest
from pysm import Event, State, StateMachine
from pysm.aio import AsyncQueuedStateMachine
from pysm.queued import QueuedStateMachine, ThreadSafeQueuedStateMachine


def graph(cls):
    """root(idle*, work(a*, b)), the transitions a handler can chase."""
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
    work.add_transition(a, b, events=['next'])
    return root, {'idle': idle, 'work': work, 'a': a, 'b': b}


def waiting(root, states, dispatch, look):
    """Run `go`, and while `a` is being entered let `dispatch` queue whatever
    it likes and `look` record what the machine says is waiting."""
    seen = []

    def on_enter(state, event):
        dispatch(root)
        seen.append(look(root))

    states['a'].handlers = {'enter': on_enter}
    root.initialize()
    root.dispatch(Event('go'))
    return seen


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_nothing_is_waiting_on_a_machine_that_is_not_running(cls):
    root, _ = graph(cls)
    root.initialize()

    assert root.pending() == []

    root.dispatch(Event('go'))

    assert root.pending() == []


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_an_event_a_handler_dispatches_is_waiting_until_the_handler_returns(cls):
    root, states = graph(cls)
    later = Event('next')

    [seen] = waiting(root, states, lambda machine: machine.dispatch(later),
                     lambda machine: machine.pending())

    assert seen == [later]
    assert root.pending() == []
    assert root.leaf_state is states['b']


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_waiting_events_come_back_in_the_order_they_will_be_handled(cls):
    """Internal before external: an event a handler dispatched is taken before
    an event that was waiting outside, which is the order the machine drains
    its queues in.

    The external event is put there by hand, from inside the handler. On this
    layer there is no other way to have one waiting while the machine runs —
    `dispatch` from a handler always defers to the internal queue — and the
    order of the two is the whole of what is being asked about.
    """
    root, states = graph(cls)
    outside = Event('outside')
    inside = Event('inside')

    def dispatch(machine):
        machine._external_queue.append(outside)
        machine.dispatch(inside)

    [seen] = waiting(root, states, dispatch, lambda machine: machine.pending())

    assert seen == [inside, outside]


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_the_list_that_comes_back_is_the_caller_s_to_keep(cls):
    root, states = graph(cls)
    later = Event('next')

    [seen] = waiting(root, states,
                     lambda machine: machine.dispatch(later),
                     lambda machine: (machine.pending(), machine.pending()))

    first, second = seen
    assert first == second
    first.append(Event('nonsense'))
    assert second == [later]


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_dropping_what_is_waiting_says_how_much_it_dropped(cls):
    root, states = graph(cls)

    def dispatch(machine):
        machine.dispatch(Event('one'))
        machine.dispatch(Event('two'))

    [seen] = waiting(root, states, dispatch,
                     lambda machine: (machine.drop_pending(),
                                      machine.pending()))

    assert seen == (2, [])
    assert root.leaf_state is states['a']


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_dropping_nothing_drops_nothing(cls):
    root, _ = graph(cls)
    root.initialize()

    assert root.drop_pending() == 0


@pytest.mark.parametrize('cls', [QueuedStateMachine, ThreadSafeQueuedStateMachine])
def test_a_machine_keeps_running_after_what_was_waiting_is_dropped(cls):
    root, states = graph(cls)

    [_] = waiting(root, states,
                  lambda machine: machine.dispatch(Event('next')),
                  lambda machine: machine.drop_pending())

    assert root.leaf_state is states['a']

    root.dispatch(Event('next'))

    assert root.leaf_state is states['b']
    assert root.pending() == []


def test_the_async_layer_answers_the_same_way():
    """Same two queues and the same order, arranged the way the async layer
    fills them for real: the handler's own dispatch is internal, and a
    dispatch from another task while the machine is busy is external."""
    async def scenario():
        root, states = graph(AsyncQueuedStateMachine)
        inside = Event('inside')
        outside = Event('outside')
        seen = []

        async def on_enter(state, event):
            await root.dispatch(inside)
            await asyncio.ensure_future(root.dispatch(outside))
            seen.append(root.pending())

        states['a'].handlers = {'enter': on_enter}
        root.initialize()
        await root.dispatch(Event('go'))
        return seen, root, [inside, outside]

    seen, root, dispatched = asyncio.run(scenario())

    [waiting_then] = seen
    assert waiting_then == dispatched
    assert root.pending() == []


def test_the_async_layer_drops_what_is_waiting_the_same_way():
    async def scenario():
        root, states = graph(AsyncQueuedStateMachine)
        seen = []

        async def on_enter(state, event):
            await root.dispatch(Event('one'))
            await root.dispatch(Event('two'))
            seen.append((root.drop_pending(), root.pending()))

        states['a'].handlers = {'enter': on_enter}
        root.initialize()
        await root.dispatch(Event('go'))
        return seen, root

    seen, root = asyncio.run(scenario())

    assert seen == [(2, [])]
    assert root.leaf_state.name == 'a'


def test_the_async_layer_is_empty_when_it_is_not_running():
    async def scenario():
        root, _ = graph(AsyncQueuedStateMachine)
        root.initialize()
        before = root.pending()
        await root.dispatch(Event('go'))
        return before, root.pending(), root.drop_pending()

    assert asyncio.run(scenario()) == ([], [], 0)
