"""Held-out tests for `StateMachine.route`.

Self-contained on purpose: grading runs with conftest loading disabled and its
pytest config pinned outside the workdir, so nothing here may lean on a
fixture file.

Every assertion is about *a* route rather than about the reference's route.
The prompt says any run of events that gets there is a correct answer, so the
suite dispatches whatever came back and looks at where the machine ends up —
a suite that compared event lists would be grading whether the agent guessed
our search order.
"""

from pysm import Event, State, StateMachine


def workshop():
    """idle -> work(cutting -> sanding(rough -> fine)) -> done.

    `restart` is a self-transition on `work` and the only way back into
    `cutting` from anywhere inside `sanding`: leaving a machine puts it back
    at its initial state, so `restart` re-enters `work` at `cutting` however
    deep in it the graph was standing. `done` is where the run ends and
    nothing leads out of it, so there is no long way round.
    """
    machine = StateMachine('workshop')
    idle = State('idle')
    work = StateMachine('work')
    cutting = State('cutting')
    sanding = StateMachine('sanding')
    rough = State('rough')
    fine = State('fine')
    done = State('done')

    machine.add_state(idle, initial=True)
    machine.add_state(work)
    machine.add_state(done)
    work.add_state(cutting, initial=True)
    work.add_state(sanding)
    sanding.add_state(rough, initial=True)
    sanding.add_state(fine)

    machine.add_transition(idle, work, events=['start'])
    work.add_transition(cutting, sanding, events=['next'])
    sanding.add_transition(rough, fine, events=['polish'])
    machine.add_transition(work, work, events=['restart'])
    machine.add_transition(work, done, events=['finish'])
    machine.initialize()
    return machine, {
        'idle': idle, 'work': work, 'cutting': cutting, 'sanding': sanding,
        'rough': rough, 'fine': fine, 'done': done,
    }


def follow(machine, events):
    for event in events:
        machine.dispatch(event)
    return machine.leaf_state


def test_route_reaches_a_state_one_transition_away():
    machine, states = workshop()

    events = machine.route(states['cutting'])

    assert events is not None
    assert follow(machine, events) is states['cutting']


def test_route_reaches_a_state_several_machines_down():
    machine, states = workshop()

    events = machine.route(states['fine'])

    assert events is not None
    assert follow(machine, events) is states['fine']


def test_route_to_where_the_machine_already_is_asks_for_nothing():
    machine, states = workshop()

    assert machine.route(states['idle']) == []


def test_route_returns_events_that_can_be_dispatched():
    machine, states = workshop()

    events = machine.route(states['done'])

    assert events is not None and events
    for event in events:
        assert isinstance(event, Event)
    assert follow(machine, events) is states['done']


def test_route_says_so_when_nothing_gets_there():
    machine, states = workshop()
    orphan = State('orphan')
    machine.add_state(orphan)

    assert machine.route(orphan) is None


def test_leaving_a_machine_puts_it_back_at_its_initial_state():
    """The transition walk resets every machine it climbs past, so a
    self-transition on `work` re-enters at `cutting` however deep inside
    `work` the machine was. A search that reads each machine's current local
    state to find where a transition lands never finds this route."""
    machine, states = workshop()
    follow(machine, [Event('start'), Event('next'), Event('polish')])
    assert machine.leaf_state is states['fine']

    events = machine.route(states['cutting'])

    assert events is not None
    assert follow(machine, events) is states['cutting']


def test_route_from_deep_inside_reaches_a_state_outside():
    machine, states = workshop()
    follow(machine, [Event('start'), Event('next'), Event('polish')])

    events = machine.route(states['done'])

    assert events is not None
    assert follow(machine, events) is states['done']


def test_route_says_so_when_the_way_back_has_been_left_behind():
    """Nothing leads out of `done`, so once the run has finished there is no
    route to anywhere else."""
    machine, states = workshop()
    follow(machine, [Event('start'), Event('finish')])
    assert machine.leaf_state is states['done']

    assert machine.route(states['idle']) is None
    assert machine.route(states['cutting']) is None


def test_working_out_a_route_leaves_the_machine_where_it_was():
    machine, states = workshop()
    follow(machine, [Event('start'), Event('next')])
    before = {
        'leaf': machine.leaf_state,
        'work': states['work'].state,
        'sanding': states['sanding'].state,
        'root': machine.state,
        'leaf_stack': list(machine.leaf_state_stack.deque),
        'work_stack': list(states['work'].state_stack.deque),
    }

    machine.route(states['done'])

    assert machine.leaf_state is before['leaf']
    assert states['work'].state is before['work']
    assert states['sanding'].state is before['sanding']
    assert machine.state is before['root']
    assert list(machine.leaf_state_stack.deque) == before['leaf_stack']
    assert list(states['work'].state_stack.deque) == before['work_stack']


def test_working_out_a_route_fires_no_handler():
    machine, states = workshop()
    seen = []
    for name in ('idle', 'cutting', 'rough', 'fine', 'done'):
        states[name].handlers = {
            'enter': lambda state, event: seen.append(state.name),
            'exit': lambda state, event: seen.append(state.name),
        }

    machine.route(states['done'])

    assert seen == []


def test_a_route_never_leans_on_a_transition_that_may_not_fire():
    """A guarded transition is the only way from `left` to `right`, and its
    guard is false. A route that used it would be a route that does not
    work."""
    machine = StateMachine('junction')
    left = State('left')
    right = State('right')
    machine.add_state(left, initial=True)
    machine.add_state(right)
    machine.add_transition(
        left, right, events=['go'], condition=lambda state, event: False)
    machine.initialize()

    assert machine.route(right) is None


def test_a_route_never_leans_on_a_transition_keyed_on_an_input():
    machine = StateMachine('junction')
    left = State('left')
    right = State('right')
    machine.add_state(left, initial=True)
    machine.add_state(right)
    machine.add_transition(left, right, events=['go'], input=['token'])
    machine.initialize()

    assert machine.route(right) is None


def test_a_route_is_not_confused_by_an_internal_transition():
    """A transition to nowhere changes no state, so it can never be a step on
    the way anywhere."""
    machine = StateMachine('ticker')
    waiting = State('waiting')
    running = State('running')
    machine.add_state(waiting, initial=True)
    machine.add_state(running)
    machine.add_transition(waiting, None, events=['tick'])
    machine.add_transition(waiting, running, events=['go'])
    machine.initialize()

    events = machine.route(running)

    assert events is not None
    assert follow(machine, events) is running


def test_a_route_out_of_a_cycle_terminates():
    """Three states in a ring and a fourth nothing reaches. The search has to
    notice it is going round."""
    machine = StateMachine('ring')
    one, two, three, aside = (
        State('one'), State('two'), State('three'), State('aside'))
    machine.add_state(one, initial=True)
    machine.add_state(two)
    machine.add_state(three)
    machine.add_state(aside)
    machine.add_transition(one, two, events=['step'])
    machine.add_transition(two, three, events=['step'])
    machine.add_transition(three, one, events=['step'])
    machine.initialize()

    assert machine.route(three) is not None
    assert machine.route(aside) is None
