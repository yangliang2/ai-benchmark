import pytest
from matchers import expand, match


def test_a_braceless_pattern_expands_to_itself():
    assert expand("plain.txt") == ["plain.txt"]


def test_a_single_group_expands_each_alternative():
    assert expand("a{b,c}d") == ["abd", "acd"]


def test_an_empty_alternative_is_allowed():
    assert expand("img{,-2x}.png") == ["img.png", "img-2x.png"]


def test_groups_nest():
    assert expand("{a,b{c,d}}") == ["a", "bc", "bd"]


def test_several_groups_multiply_left_to_right():
    assert expand("{a,b}{1,2}") == ["a1", "a2", "b1", "b2"]


def test_a_comma_outside_any_group_is_literal():
    assert expand("a,b") == ["a,b"]


def test_escaped_braces_are_literal():
    assert expand(r"a\{b,c\}") == ["a{b,c}"]


def test_an_escaped_comma_does_not_split_alternatives():
    assert expand(r"{b\,c,d}") == ["b,c", "d"]


def test_an_unclosed_group_raises():
    with pytest.raises(ValueError):
        expand("a{b,c")


def test_a_stray_closing_brace_raises():
    with pytest.raises(ValueError):
        expand("a}b")


def test_existing_behaviour_is_preserved():
    assert match("*.txt", "notes.txt")
    assert not match("?.txt", "notes.txt")
