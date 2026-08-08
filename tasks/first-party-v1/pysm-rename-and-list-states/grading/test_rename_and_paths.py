"""Held-out tests for StateMachineBuilder.rename and .paths.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.
"""

import pytest
from pysm import Event, StateMachineException
from pysm.builder import StateMachineBuilder


def nested():
    """root(outer(leaf*)*, spare), the smallest build with a subtree in it."""
    builder = StateMachineBuilder('root')
    builder.machine('outer', initial=True)
    builder.state('leaf', initial=True, parent_path='outer')
    builder.state('spare')
    return builder


def test_a_renamed_state_answers_to_its_new_name():
    builder = nested()

    builder.rename('spare', 'reserve')

    assert builder.paths() == [
        ('root',), ('root', 'outer'), ('root', 'outer', 'leaf'),
        ('root', 'reserve'),
    ]


def test_renaming_moves_the_states_underneath_it():
    """The paths the builder resolves are made of names, so a subtree whose
    root was renamed is a subtree whose every path changed."""
    builder = nested()

    builder.rename('outer', 'shell')

    assert builder.paths() == [
        ('root',), ('root', 'shell'), ('root', 'shell', 'leaf'),
        ('root', 'spare'),
    ]
    builder.state('second', parent_path='shell')
    assert ('root', 'shell', 'second') in builder.paths()


def test_the_machine_that_is_built_carries_the_new_name():
    builder = nested()

    builder.rename('outer', 'shell')
    machine = builder.build()

    assert machine.state.name == 'shell'
    assert machine.leaf_state.name == 'leaf'


def test_the_root_can_be_renamed():
    builder = nested()

    builder.rename('root', 'top')

    assert builder.paths() == [
        ('top',), ('top', 'outer'), ('top', 'outer', 'leaf'), ('top', 'spare'),
    ]
    assert builder.build().name == 'top'


def test_a_name_a_sibling_already_uses_is_refused_and_changes_nothing():
    builder = nested()
    before = builder.paths()

    with pytest.raises(StateMachineException):
        builder.rename('outer', 'spare')

    assert builder.paths() == before
    assert builder.build().state.name == 'outer'


def test_renaming_a_state_to_the_name_it_has_is_allowed():
    builder = nested()
    before = builder.paths()

    builder.rename('outer', 'outer')

    assert builder.paths() == before


def test_a_name_that_could_not_be_written_as_a_path_is_refused():
    """A string path is read by splitting it on `/`, and a state named with
    one in it could never be reached by that spelling. An empty name reaches
    nothing either."""
    builder = nested()

    for name in ('', 'in/out'):
        with pytest.raises(StateMachineException):
            builder.rename('spare', name)

    assert ('root', 'spare') in builder.paths()


def test_renaming_something_that_was_never_added_is_refused():
    builder = nested()

    with pytest.raises(StateMachineException):
        builder.rename('missing', 'found')


def test_renaming_hands_the_builder_back():
    builder = nested()

    assert builder.rename('spare', 'reserve') is builder


def test_the_paths_come_back_with_the_root_first_and_the_rest_in_order():
    builder = StateMachineBuilder('zulu')
    builder.state('bravo', initial=True)
    builder.state('alpha')

    assert builder.paths() == [('zulu',), ('zulu', 'alpha'), ('zulu', 'bravo')]


def test_asking_for_the_paths_builds_nothing():
    builder = nested()
    before = builder.paths()

    builder.paths()

    assert builder.paths() == before
    machine = builder.build()
    machine.dispatch(Event('nothing-registered'))
    assert machine.leaf_state.name == 'leaf'
