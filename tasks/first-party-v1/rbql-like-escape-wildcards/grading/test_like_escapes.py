"""Held-out grading suite for backslash escapes in like() patterns.

Most of what is checked here is not the escape but the contracts around it.
A pattern is anchored at both ends; everything that is not a wildcard is
matched literally however much it looks like a regular expression, which is
what re.escape over the runs between wildcards is for; a backslash that
escapes nothing is itself literal; and the operator caches one compiled
matcher per pattern, so two patterns in one query must not answer for each
other. The feature is a dozen lines; these are what the dozen lines have to
leave standing.

Nothing here asserts the regex a pattern translates to — a pattern is asked
whether it matches a string, which is the only thing like() promises anyone.
"""

import re

import rbql
from rbql import rbql_engine


def matches(pattern, text):
    """Whether like() would say this pattern matches this text."""
    return re.match(rbql_engine.like_to_regex(pattern), text) is not None


def selected(query, column):
    """The one-column table a query keeps."""
    output, warnings = [], []
    rbql.query_table(query, [[value] for value in column], output, warnings)
    assert warnings == [], warnings
    return [record[0] for record in output]


# --- the escape itself ----------------------------------------------------------


def test_an_escaped_percent_matches_only_a_percent():
    assert matches(r'100\%', '100%')
    assert not matches(r'100\%', '100')
    assert not matches(r'100\%', '100 out of 100')


def test_an_escaped_underscore_matches_only_an_underscore():
    assert matches(r'a\_b', 'a_b')
    assert not matches(r'a\_b', 'axb')
    assert not matches(r'a\_b', 'ab')


def test_an_escaped_backslash_matches_one_backslash():
    assert matches(r'a\\b', 'a\\b')
    assert not matches(r'a\\b', 'ab')
    assert not matches(r'a\\b', 'a\\\\b')


def test_an_escaped_backslash_does_not_swallow_the_wildcard_after_it():
    """The two-character escape is consumed whole, so the `%` that follows a
    `\\\\` is still a wildcard rather than the escaped character."""
    assert matches(r'a\\%', 'a\\')
    assert matches(r'a\\%', 'a\\anything at all')
    assert not matches(r'a\\%', 'a')
    assert not matches(r'a\\%', 'ab')


def test_an_escape_at_the_front_of_the_pattern_still_leaves_the_rest_alone():
    assert matches(r'\%%', '%and more')
    assert matches(r'\%%', '%')
    assert not matches(r'\%%', 'and more')


# --- a backslash that escapes nothing -------------------------------------------


def test_a_backslash_before_an_ordinary_character_is_literal():
    assert matches(r'a\b', 'a\\b')
    assert not matches(r'a\b', 'ab')
    assert not matches(r'a\b', 'a\tb')


def test_a_backslash_at_the_very_end_of_a_pattern_is_literal():
    assert matches('a\\', 'a\\')
    assert not matches('a\\', 'a')


def test_a_backslash_before_a_regex_metacharacter_is_still_two_literals():
    assert matches(r'a\.c', 'a\\.c')
    assert not matches(r'a\.c', 'a.c')
    assert not matches(r'a\.c', 'abc')


# --- what the wildcards did before, and still do --------------------------------


def test_an_unescaped_percent_still_matches_any_run():
    assert matches('%bar', 'foobar')
    assert matches('%bar', 'bar')
    assert not matches('%bar', 'barred')


def test_an_unescaped_underscore_still_matches_exactly_one_character():
    assert matches('a_c', 'abc')
    assert not matches('a_c', 'ac')
    assert not matches('a_c', 'abbc')


def test_a_pattern_is_still_anchored_at_both_ends():
    assert matches('abc', 'abc')
    assert not matches('abc', 'xabc')
    assert not matches('abc', 'abcx')


def test_regex_metacharacters_in_a_pattern_are_still_matched_literally():
    assert matches('a.c', 'a.c')
    assert not matches('a.c', 'abc')
    assert matches('a*+[c]', 'a*+[c]')
    assert not matches('a*+[c]', 'aa')
    assert matches('(a|b)', '(a|b)')
    assert not matches('(a|b)', 'a')


def test_the_mixed_pattern_the_repository_already_pins_still_behaves():
    """The one case the visible suite spells out, asked as behaviour: two
    wildcards around a run whose dot and star are literal."""
    assert matches('%hello_world.foo.*bar%', 'say hello world.foo.*bar now')
    assert not matches('%hello_world.foo.*bar%', 'say hello world.fooXXbar now')


# --- through the operator, not just the translation ------------------------------


def test_the_like_operator_uses_the_escape():
    column = ['100%', '100X', '100', 'x100%y']

    assert selected(r"select a1 where like(a1, '100\\%')", column) == ['100%']


def test_the_like_operator_still_reads_an_unescaped_wildcard_as_one():
    column = ['100%', '100X', '100', 'x100%y']

    assert selected("select a1 where like(a1, '100_')", column) == ['100%', '100X']


def test_two_patterns_in_one_query_do_not_answer_for_each_other():
    """One compiled matcher is cached per pattern, so an escaped and an
    unescaped pattern used in the same query must stay apart."""
    column = ['100%', '100X']
    query = r"select a1 where like(a1, '100\\%') or like(a1, '100X')"

    assert selected(query, column) == ['100%', '100X']

    query = r"select a1 where like(a1, '100\\%') and not like(a1, '100_')"

    assert selected(query, column) == []
