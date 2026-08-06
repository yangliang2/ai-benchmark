"""Structural half of the grading suite: asserts the quoting decision really
moved into csv_utils and that CSVWriter no longer makes it itself. Fails on
the pristine repository, where get_polymorphic_quote_function does not exist.

What is deliberately *not* asserted here is which quoter comes back for
`quoted` and for `quoted_rfc`. That is what the writer does with it, it is
what the behaviour half pins, and a structural assertion about it would let a
merged quoter fail for looking wrong rather than for writing the wrong thing.
"""

import ast
import inspect
import textwrap

import pytest
from rbql import csv_utils, rbql_csv


def test_the_quoting_choice_is_a_function_of_csv_utils():
    assert callable(csv_utils.get_polymorphic_quote_function)


@pytest.mark.parametrize("policy", ["quoted", "quoted_rfc"])
def test_a_quoting_policy_gets_a_function_that_quotes_one_field(policy):
    quote = csv_utils.get_polymorphic_quote_function(',', policy)

    assert callable(quote)
    assert isinstance(quote('a'), str)


@pytest.mark.parametrize("policy", ["simple", "whitespace", "monocolumn"])
def test_a_policy_that_quotes_nothing_gets_nothing_back(policy):
    assert csv_utils.get_polymorphic_quote_function(',', policy) is None


def test_an_unsupported_policy_is_refused_the_way_splitting_refuses_one():
    with pytest.raises(ValueError):
        csv_utils.get_polymorphic_quote_function(',', 'rfc4180')


def test_the_writer_no_longer_carries_a_second_quoting_method():
    assert not hasattr(rbql_csv.CSVWriter, 'quote_fields_rfc')


def test_the_writer_no_longer_picks_the_rfc_quoter_itself():
    """The call, not the mention: CSVWriter may still be documented in terms
    of the two policies — in a comment, in a docstring, wherever prose goes —
    it just may not reach for the rfc quoting function, because choosing
    between the two is now somebody else's job.

    So the class is read as a syntax tree rather than as text, and what is
    looked for is the name in a position that names the function: bare, or as
    an attribute off csv_utils. A class that only talks about it carries no
    such node; a class that reaches for it the way the pristine one does
    carries one.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(rbql_csv.CSVWriter)))
    used = {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if isinstance(node, (ast.Name, ast.Attribute))
    }

    assert 'rfc_quote_field' not in used
