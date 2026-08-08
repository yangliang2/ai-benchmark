import pytest
from sieve import FALSE, TRUE, UNKNOWN, compare, field_names, kind_of, select_equal

PEOPLE = [
    {"name": "ada", "age": 36, "active": True},
    {"name": "bo", "age": None, "active": False},
    {"name": "cy", "age": 36},
]


def test_field_names_gathers_every_field_in_name_order():
    assert field_names(PEOPLE) == ["active", "age", "name"]


def test_field_names_of_nothing_is_nothing():
    assert field_names([]) == []


def test_kind_of_keeps_booleans_apart_from_numbers():
    assert kind_of(True) == "boolean"
    assert kind_of(1) == "number"
    assert kind_of(1.5) == "number"
    assert kind_of("1") == "string"
    assert kind_of(None) == "unknown"


def test_kind_of_refuses_a_value_no_record_may_hold():
    with pytest.raises(ValueError):
        kind_of([1, 2])


def test_comparing_known_numbers():
    assert compare(3, "=", 3) == TRUE
    assert compare(3, "!=", 3) == FALSE
    assert compare(3, "<", 4) == TRUE
    assert compare(3.5, ">=", 3) == TRUE


def test_comparing_strings_character_by_character():
    assert compare("ada", "<", "bo") == TRUE
    assert compare("ada", "=", "ada") == TRUE


def test_false_sorts_before_true():
    assert compare(False, "<", True) == TRUE
    assert compare(True, ">=", True) == TRUE


def test_anything_compared_with_the_unknown_is_unknown():
    assert compare(None, "=", 3) == UNKNOWN
    assert compare(3, "!=", None) == UNKNOWN
    assert compare(None, "<", None) == UNKNOWN


def test_two_kinds_are_never_equal():
    assert compare(1, "=", "1") == FALSE
    assert compare(1, "!=", "1") == TRUE
    assert compare(True, "=", 1) == FALSE


def test_two_kinds_are_never_ordered():
    with pytest.raises(ValueError):
        compare(1, "<", "1")
    with pytest.raises(ValueError):
        compare(True, ">", 0)


def test_an_operator_the_module_does_not_have():
    with pytest.raises(ValueError):
        compare(1, "==", 1)


def test_select_equal_keeps_order_and_drops_the_unknown():
    assert select_equal(PEOPLE, "age", 36) == [PEOPLE[0], PEOPLE[2]]
    assert select_equal(PEOPLE, "age", None) == []
    assert select_equal(PEOPLE, "active", False) == [PEOPLE[1]]


def test_select_equal_skips_a_record_without_the_field():
    assert select_equal(PEOPLE, "nickname", "x") == []
