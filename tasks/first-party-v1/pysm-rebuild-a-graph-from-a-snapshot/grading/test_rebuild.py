"""Held-out tests for `pysm.serialization.rebuild`.

Self-contained on purpose: grading runs with conftest loading disabled and its
pytest config pinned outside the workdir, so nothing here may lean on a
fixture file.

What the suite grades is the round trip and the shape of the graph that comes
back, never which state a machine was given as its initial one. The snapshot
format does not record that, the prompt says any of a machine's own states
will do, and a suite pinning one choice would be grading whether the agent
guessed ours.
"""

import pytest

from pysm import Event, State, StateMachine, StateMachineException
from pysm import serialization
from pysm.serialization import restore, snapshot

# A version this library has never written. Named rather than inlined so
# the test below reads as the refusal it is asking for.
UNKNOWN_VERSION = 99


def rebuild(data):
    """The function under test, looked up when a test runs rather than at
    import time, so a repository that does not have it yet fails every test
    on its own terms instead of failing collection."""
    return serialization.rebuild(data)


def workshop():
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
    machine.add_transition(work, done, events=['finish'])
    machine.initialize()
    return machine


def moved():
    machine = workshop()
    machine.dispatch(Event('start'))
    machine.dispatch(Event('next'))
    machine.dispatch(Event('polish'))
    return machine


def without_metadata(data):
    plain = dict(data)
    plain.pop('metadata', None)
    return plain


def named(state):
    return None if state is None else state.name


def children_of(machine):
    return sorted(state.name for state in machine.states)


def test_a_rebuilt_graph_snapshots_back_to_the_snapshot_it_came_from():
    data = snapshot(moved())

    assert snapshot(rebuild(data)) == data


def test_a_rebuilt_graph_of_a_machine_standing_at_its_initial_states():
    data = snapshot(workshop())

    assert snapshot(rebuild(data)) == data


def test_the_root_comes_back_as_a_machine_with_the_right_name():
    root = rebuild(snapshot(moved()))

    assert isinstance(root, StateMachine)
    assert root.name == 'workshop'
    assert root.parent is None


def test_the_states_come_back_wired_into_the_shape_their_paths_describe():
    root = rebuild(snapshot(moved()))

    assert children_of(root) == ['done', 'idle', 'work']
    work = [state for state in root.states if state.name == 'work'][0]
    assert isinstance(work, StateMachine)
    assert work.parent is root
    assert children_of(work) == ['cutting', 'sanding']
    sanding = [state for state in work.states if state.name == 'sanding'][0]
    assert isinstance(sanding, StateMachine)
    assert children_of(sanding) == ['fine', 'rough']


def test_a_state_with_no_states_under_it_does_not_come_back_as_a_machine():
    root = rebuild(snapshot(moved()))

    idle = [state for state in root.states if state.name == 'idle'][0]
    assert not isinstance(idle, StateMachine)
    assert isinstance(idle, State)


def test_the_rebuilt_graph_stands_where_the_snapshot_said():
    root = rebuild(snapshot(moved()))

    assert named(root.leaf_state) == 'fine'
    work = [state for state in root.states if state.name == 'work'][0]
    assert named(root.state) == 'work'
    assert named(work.state) == 'sanding'
    sanding = [state for state in work.states if state.name == 'sanding'][0]
    assert named(sanding.state) == 'fine'


def test_the_history_the_snapshot_carried_comes_back_with_it():
    data = snapshot(moved())
    assert data['leaf_state_stack']

    root = rebuild(data)

    assert [state.name for state in root.leaf_state_stack.deque] == [
        path[-1] for path in data['leaf_state_stack']]
    work = [state for state in root.states if state.name == 'work'][0]
    assert [state.name for state in work.state_stack.deque] == [
        path[-1] for path in [
            item['state_stack'] for item in data['machines']
            if item['path'] == ['workshop', 'work']][0]]


def test_the_graph_the_snapshot_came_from_is_not_needed_and_not_touched():
    original = moved()
    data = snapshot(original)

    rebuild(data)

    assert original.leaf_state.name == 'fine'
    assert snapshot(original) == data


def test_the_snapshot_itself_is_not_written_into():
    data = snapshot(moved())
    before = snapshot(moved())

    rebuild(data)

    assert data == before


def test_a_rebuilt_graph_accepts_the_snapshot_it_was_built_from():
    data = snapshot(moved())

    root = rebuild(data)

    assert restore(root, data) is root
    assert root.leaf_state.name == 'fine'


def test_a_rebuilt_graph_accepts_another_snapshot_of_the_same_graph():
    early = snapshot(workshop())
    late = snapshot(moved())

    root = rebuild(late)
    restore(root, early)

    assert root.leaf_state.name == 'idle'


def test_metadata_is_not_part_of_the_graph():
    plain = snapshot(moved())
    tagged = snapshot(moved(), metadata={'note': 'anything at all'})

    assert without_metadata(snapshot(rebuild(tagged))) == plain


def test_two_graphs_rebuilt_from_one_snapshot_stand_the_same_way():
    data = snapshot(moved())

    assert snapshot(rebuild(data)) == snapshot(rebuild(data))


def test_states_of_the_same_name_in_different_branches_stay_apart():
    machine = StateMachine('root')
    left = StateMachine('left')
    right = StateMachine('right')
    machine.add_state(left, initial=True)
    machine.add_state(right)
    left.add_state(State('ready'), initial=True)
    right.add_state(State('ready'), initial=True)
    machine.initialize()
    data = snapshot(machine)

    root = rebuild(data)

    assert snapshot(root) == data
    rebuilt_left = [state for state in root.states if state.name == 'left'][0]
    rebuilt_right = [state for state in root.states if state.name == 'right'][0]
    assert rebuilt_left.state is not rebuilt_right.state


def test_a_machine_with_nothing_under_it_comes_back_as_an_empty_machine():
    machine = StateMachine('root')
    empty = StateMachine('empty')
    machine.add_state(empty, initial=True)
    machine.initialize()
    data = snapshot(machine)

    root = rebuild(data)

    assert snapshot(root) == data
    rebuilt = [state for state in root.states if state.name == 'empty'][0]
    assert isinstance(rebuilt, StateMachine)
    assert rebuilt.states == set()


def test_the_rebuilt_graph_is_one_a_machine_can_be_started_from_again():
    """Which state a machine is given as its initial one is the snapshot's
    silence and the author's choice. What a choice may not be is illegal: the
    graph has to initialize, and initializing it has to leave every machine
    holding one of its own states."""
    root = rebuild(snapshot(moved()))

    root.initialize()

    assert root.state in root.states
    work = [state for state in root.states if state.name == 'work'][0]
    assert work.state in work.states
    sanding = [state for state in work.states if state.name == 'sanding'][0]
    assert sanding.state in sanding.states
    assert root.leaf_state in (sanding.states | work.states | root.states)


def test_a_snapshot_from_a_version_this_library_does_not_know_is_refused():
    data = snapshot(moved())
    data['version'] = UNKNOWN_VERSION

    with pytest.raises(StateMachineException):
        rebuild(data)


def test_a_snapshot_naming_a_state_with_no_parent_in_it_is_refused():
    data = snapshot(moved())
    data['states'].append(['workshop', 'missing', 'orphan'])

    with pytest.raises(StateMachineException):
        rebuild(data)


def test_a_snapshot_whose_root_is_not_one_of_its_machines_is_refused():
    data = snapshot(moved())
    data['machines'] = [item for item in data['machines']
                        if item['path'] != ['workshop']]

    with pytest.raises(StateMachineException):
        rebuild(data)
