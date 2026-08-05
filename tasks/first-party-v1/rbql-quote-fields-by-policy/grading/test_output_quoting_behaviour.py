"""Behaviour half of the grading suite: what CSVWriter puts on the stream
under each policy, and the warnings it reports for it.

The whole point of the pair of quoting functions is one clause: the rfc
quoter also quotes a field that carries a newline or a carriage return, and
the plain one does not, because only quoted_rfc readers know how to put such
a record back together. A merged quoter that keeps either behaviour for both
policies satisfies everything the prompt asks for and breaks that, so the
cases below are spelled out per policy rather than checked against each
other. Everything here passes on the pristine repository.

Nothing in this file computes an expectation with the code under test: every
line the writer should produce is written out literally.
"""

import io

import pytest
from rbql import rbql_csv, rbql_engine


def written(table, delim, policy, header=None):
    """The text a CSVWriter puts on its stream, and the warnings it reports."""
    stream = io.StringIO()
    writer = rbql_csv.CSVWriter(stream, False, None, delim, policy, '\n')
    if header is not None:
        writer.set_header(header)
    writer._write_all(table)
    return stream.getvalue(), writer.get_warnings()


def test_the_quoted_policy_quotes_a_field_holding_the_delimiter_or_a_quote():
    text, warnings = written(
        [['plain', 'a,b'], ['a"b', 'a""b'], ['', ' padded ']], ',', 'quoted'
    )

    assert text == 'plain,"a,b"\n"a""b","a""""b"\n, padded \n'
    assert warnings == []


def test_the_quoted_policy_leaves_a_newline_inside_a_field_unquoted():
    """The clause the rfc quoter adds, read from the other side: under
    `quoted` a line break inside a field is written bare, which is what makes
    the record unreadable again and why quoted_rfc exists at all."""
    text, warnings = written([['a\nb', 'c\rd'], ['e\r\nf', 'g']], ',', 'quoted')

    assert text == 'a\nb,c\rd\ne\r\nf,g\n'
    assert warnings == []


def test_the_rfc_policy_quotes_a_field_holding_a_line_break():
    text, warnings = written([['a\nb', 'c\rd'], ['e\r\nf', 'g']], ',', 'quoted_rfc')

    assert text == '"a\nb","c\rd"\n"e\r\nf",g\n'
    assert warnings == []


def test_the_rfc_policy_quotes_the_delimiter_and_the_quote_the_same_way():
    text, warnings = written(
        [['plain', 'a,b'], ['a"b', 'a""b'], ['', ' padded ']], ',', 'quoted_rfc'
    )

    assert text == 'plain,"a,b"\n"a""b","a""""b"\n, padded \n'
    assert warnings == []


def test_quoting_follows_the_writers_own_delimiter():
    """Not a comma: the field that gets quoted is the one holding *this*
    writer's delimiter, and a comma in a semicolon-separated table is
    ordinary text."""
    for policy in ('quoted', 'quoted_rfc'):
        text, warnings = written([['a;b', 'a,b']], ';', policy)

        assert text == '"a;b";a,b\n', policy
        assert warnings == []


def test_the_simple_policy_quotes_nothing_and_says_so_afterwards():
    text, warnings = written([['a,b', 'c']], ',', 'simple')

    assert text == 'a,b,c\n'
    assert warnings == ['Some output fields contain separator']


def test_the_whitespace_policy_quotes_nothing():
    text, warnings = written([['a b', 'c']], ' ', 'whitespace')

    assert text == 'a b c\n'
    assert warnings == ['Some output fields contain separator']


def test_the_monocolumn_policy_writes_the_one_field_untouched():
    text, warnings = written([['a,b"c'], ['d\ne']], ',', 'monocolumn')

    assert text == 'a,b"c\nd\ne\n'
    assert warnings == []


def test_the_monocolumn_policy_refuses_a_record_with_two_fields():
    with pytest.raises(rbql_engine.RbqlIOHandlingError):
        written([['a', 'b']], ',', 'monocolumn')


def test_an_unknown_policy_is_still_refused_when_the_writer_is_built():
    with pytest.raises(RuntimeError):
        rbql_csv.CSVWriter(io.StringIO(), False, None, ',', 'rfc4180', '\n')


def test_none_becomes_an_empty_field_and_is_reported():
    text, warnings = written([['a', None]], ',', 'quoted')

    assert text == 'a,\n'
    assert warnings == ['None values in output were replaced by empty strings']


def test_a_list_field_is_flattened_before_it_is_quoted():
    """normalize_fields runs first and joins a list with the sub-array
    delimiter; the quoting then sees one field, and that field holds a
    delimiter only if the sub-array delimiter is the writer's own."""
    text, warnings = written([['a', ['x', 'y']]], ',', 'quoted')

    assert text == 'a,x|y\n'
    assert warnings == []


def test_the_header_is_written_through_the_same_quoting():
    text, warnings = written([['x,y']], ',', 'quoted', header=['a,b'])

    assert text == '"a,b"\n"x,y"\n'
    assert warnings == []


def test_a_record_that_does_not_match_the_header_is_refused():
    with pytest.raises(rbql_engine.RbqlIOHandlingError):
        written([['x', 'y']], ',', 'quoted', header=['a'])
