"""Held-out tests for refusing snapshot metadata that is not plain data.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.
"""

import pytest
from pysm import Event, State, StateMachine, StateMachineException
from pysm.serialization import restore, snapshot


def graph():
    """root(idle*, work(a*, b))."""
    root = StateMachine('root')
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
    root.initialize()
    return root, {'idle': idle, 'work': work, 'a': a, 'b': b}


class Anything:
    """Something a snapshot could not be written out with."""


PLAIN = [
    'a string',
    7,
    -1.5,
    True,
    False,
    [],
    {},
    ['a', 1, None, True],
    {'who': 'us', 'when': 3, 'why': None},
    {'nested': {'deeper': ['and', {'deeper': [1.0]}]}},
    [[[['bottom']]]],
]

NOT_PLAIN = [
    Anything(),
    ('a', 'tuple'),
    {'ok', 'a set'},
    b'bytes',
    {'holding': Anything()},
    {'holding': ('a', 'tuple')},
    ['fine', 'fine', Anything()],
    {'deep': {'deeper': [1, 2, Anything()]}},
    {'deep': [{'deeper': b'bytes'}]},
    [[[Anything()]]],
    {1: 'an int key'},
    {None: 'no key at all'},
    {'outer': {2.5: 'a float key'}},
]


@pytest.mark.parametrize('metadata', PLAIN, ids=repr)
def test_plain_metadata_travels_with_the_snapshot(metadata):
    root, _ = graph()

    data = snapshot(root, metadata=metadata)

    assert data['metadata'] == metadata


@pytest.mark.parametrize('metadata', NOT_PLAIN, ids=repr)
def test_metadata_that_is_not_plain_data_is_refused(metadata):
    root, _ = graph()

    with pytest.raises(StateMachineException):
        snapshot(root, metadata=metadata)


def test_a_refused_snapshot_is_not_returned_at_all():
    root, _ = graph()

    try:
        result = snapshot(root, metadata=Anything())
    except StateMachineException:
        result = None

    assert result is None


def test_asking_for_no_metadata_is_not_asking_for_metadata():
    """The default is absence, not an empty value: nothing is checked and no
    `metadata` key is written."""
    root, _ = graph()

    data = snapshot(root)

    assert 'metadata' not in data


def test_metadata_that_is_plain_but_empty_still_travels():
    """Whether metadata was passed is decided the way it always was, so a
    falsy value is metadata like any other."""
    root, _ = graph()

    for empty in ({}, [], '', 0, False):
        assert snapshot(root, metadata=empty)['metadata'] == empty


def test_the_snapshot_is_otherwise_what_it_was():
    root, states = graph()
    data = snapshot(root, metadata={'note': 'before'})

    root.dispatch(Event('go'))
    root.dispatch(Event('next'))
    assert root.leaf_state is states['b']

    restore(root, data)

    assert root.leaf_state is states['idle']
    assert data['leaf_state'] == ['root', 'idle']


def test_a_snapshot_carrying_metadata_still_restores():
    """`restore` reads what `snapshot` writes and ignores the rest, which is
    what the metadata is: nothing is checked on the way back in."""
    root, states = graph()
    data = snapshot(root, metadata={'note': 'before'})
    data['metadata'] = Anything()

    restore(root, data)

    assert root.leaf_state is states['idle']
