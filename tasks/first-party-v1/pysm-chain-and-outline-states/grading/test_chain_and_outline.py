"""Held-out tests for StateMachineBuilder.chain and .outline.

Self-contained on purpose: grading runs with conftest loading disabled, so
everything these tests need is built here.
"""

import pytest
from pysm import Event, StateMachineException
from pysm.builder import StateMachineBuilder


def lights():
    """A three-state run under the root, moving on `tick`."""
    builder = StateMachineBuilder('lights')
    builder.chain(['red', 'amber', 'green'], 'tick', initial=True)
    return builder


def test_a_chain_adds_its_states_in_order_and_links_each_to_the_next():
    machine = lights().build()

    assert machine.leaf_state.name == 'red'
    machine.dispatch(Event('tick'))
    assert machine.leaf_state.name == 'amber'
    machine.dispatch(Event('tick'))
    assert machine.leaf_state.name == 'green'


def test_a_chain_does_not_come_round_again():
    """The last state is the end of the run: nothing goes back to the first."""
    machine = lights().build()
    for _ in range(3):
        machine.dispatch(Event('tick'))

    assert machine.leaf_state.name == 'green'


def test_a_chain_can_be_asked_to_start_the_machine_or_not_to():
    builder = StateMachineBuilder('root')
    builder.state('waiting', initial=True)
    builder.chain(['first', 'second'], 'tick')

    machine = builder.build()

    assert machine.leaf_state.name == 'waiting'


def test_a_chain_goes_under_the_machine_it_was_given():
    builder = StateMachineBuilder('root')
    builder.machine('inner', initial=True)
    builder.chain(['one', 'two'], 'step', parent_path='inner', initial=True)

    machine = builder.build()

    assert machine.leaf_state.name == 'one'
    machine.dispatch(Event('step'))
    assert machine.leaf_state.name == 'two'


def test_a_chain_takes_its_events_as_one_name_or_as_several():
    builder = StateMachineBuilder('root')
    builder.chain(['one', 'two'], ['step', 'nudge'], initial=True)

    machine = builder.build()
    machine.dispatch(Event('nudge'))

    assert machine.leaf_state.name == 'two'


def test_a_chain_of_fewer_than_two_states_is_refused():
    builder = StateMachineBuilder('root')

    with pytest.raises(StateMachineException):
        builder.chain(['only'], 'tick')

    assert builder.outline() == ('root', 'machine', False, ())


def test_a_chain_that_repeats_a_name_is_refused_and_adds_nothing():
    builder = StateMachineBuilder('root')

    with pytest.raises(StateMachineException):
        builder.chain(['one', 'two', 'one'], 'tick')

    assert builder.outline() == ('root', 'machine', False, ())


def test_a_chain_meeting_a_name_already_there_is_refused_and_adds_nothing():
    """Refused as a whole. The collision is on the last of the three, so a
    builder that adds as it goes leaves two states behind it."""
    builder = StateMachineBuilder('root')
    builder.state('green', initial=True)

    with pytest.raises(StateMachineException):
        builder.chain(['red', 'amber', 'green'], 'tick')

    assert builder.outline() == (
        'root', 'machine', False, (('green', 'state', True, ()),)
    )


def test_a_chain_hands_the_builder_back():
    builder = StateMachineBuilder('root')

    assert builder.chain(['one', 'two'], 'tick', initial=True) is builder


def test_the_outline_reports_what_has_been_built():
    builder = StateMachineBuilder('root')
    builder.machine('outer', initial=True)
    builder.state('leaf', initial=True, parent_path='outer')
    builder.state('spare')

    assert builder.outline() == (
        'root', 'machine', False, (
            ('outer', 'machine', True, (('leaf', 'state', True, ()),)),
            ('spare', 'state', False, ()),
        )
    )


def test_the_outline_puts_the_states_under_one_parent_in_name_order():
    builder = StateMachineBuilder('root')
    builder.chain(['red', 'amber', 'green'], 'tick', initial=True)

    _, _, _, children = builder.outline()

    assert [name for name, _, _, _ in children] == ['amber', 'green', 'red']


def test_the_outline_can_be_asked_about_one_part_of_the_build():
    builder = StateMachineBuilder('root')
    builder.machine('outer', initial=True)
    builder.chain(['one', 'two'], 'step', parent_path='outer', initial=True)

    assert builder.outline('outer') == (
        'outer', 'machine', True, (
            ('one', 'state', True, ()),
            ('two', 'state', False, ()),
        )
    )


def test_asking_for_the_outline_builds_nothing():
    builder = StateMachineBuilder('root')
    builder.chain(['one', 'two'], 'tick', initial=True)
    before = builder.outline()

    builder.outline()

    assert builder.outline() == before
    assert builder.build().leaf_state.name == 'one'
