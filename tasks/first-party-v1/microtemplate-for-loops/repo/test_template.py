import pytest

from template import render


def test_placeholders_are_substituted():
    assert render("Hello {{ name }}", {"name": "Ada"}) == "Hello Ada"


def test_values_are_stringified():
    assert render("{{ n }} items", {"n": 3}) == "3 items"


def test_a_filter_pipes_the_value():
    assert render("{{ name|upper }}", {"name": "ada"}) == "ADA"


def test_a_missing_name_raises():
    with pytest.raises(KeyError):
        render("{{ ghost }}", {})


def test_an_unknown_filter_raises():
    with pytest.raises(ValueError):
        render("{{ name|shout }}", {"name": "ada"})
