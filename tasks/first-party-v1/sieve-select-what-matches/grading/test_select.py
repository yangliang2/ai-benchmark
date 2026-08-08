"""Held-out tests for `sieve.select`.

Self-contained on purpose: grading runs with conftest loading disabled and its
pytest config pinned outside the workdir, so nothing here may lean on a
fixture file.

The suite is wide because the contract is: this is a headroom anchor, and what
it measures is whether an answer gets *every* clause of a spec that states
them all. Each test names one clause of the brief.
"""

import pytest
import sieve

PEOPLE = [
    {"name": "ada", "age": 36, "active": True, "city": "york"},
    {"name": "bo", "age": None, "active": False, "city": "york"},
    {"name": "cy", "age": 7, "active": True, "city": "leeds"},
    {"name": "di", "age": 71, "active": False},
]


def select(records, expression):
    """Looked up when a test runs rather than at import time, so a module
    that does not have it yet fails every test on its own terms instead of
    failing collection."""
    return sieve.select(records, expression)


def picked(expression, records=PEOPLE):
    return [record["name"] for record in select(records, expression)]


# --- the shape of the answer ---------------------------------------------------


def test_the_records_come_back_in_the_order_they_were_given():
    assert picked("active = TRUE OR active = FALSE") == [
        "ada", "bo", "cy", "di"]


def test_the_records_that_come_back_are_the_ones_that_went_in():
    kept = select(PEOPLE, "city = 'york'")

    assert [record is PEOPLE[index] for index, record in
            zip((0, 1), kept)] == [True, True]


def test_neither_the_list_nor_the_records_are_changed():
    before = [dict(record) for record in PEOPLE]

    select(PEOPLE, "age > 10")

    assert PEOPLE == before
    assert len(PEOPLE) == 4


def test_nothing_matching_is_an_empty_list():
    assert picked("age > 1000") == []


# --- the tests themselves ------------------------------------------------------


def test_equality_and_its_negation():
    assert picked("city = 'york'") == ["ada", "bo"]
    assert picked("city != 'york'") == ["cy"]


def test_the_four_orderings():
    assert picked("age < 36") == ["cy"]
    assert picked("age <= 36") == ["ada", "cy"]
    assert picked("age > 36") == ["di"]
    assert picked("age >= 36") == ["ada", "di"]


def test_is_null_covers_the_known_unknown_and_the_missing_field():
    assert picked("age IS NULL") == ["bo"]
    assert picked("city IS NULL") == ["di"]


def test_is_not_null_is_the_other_way_round_and_never_unknown():
    assert picked("age IS NOT NULL") == ["ada", "cy", "di"]
    assert picked("city IS NOT NULL") == ["ada", "bo", "cy"]


def test_in_takes_a_list_of_values():
    assert picked("name IN ('ada', 'cy')") == ["ada", "cy"]
    assert picked("age IN (7)") == ["cy"]


def test_in_with_values_of_more_than_one_kind():
    assert picked("age IN (7, 'seven', TRUE)") == ["cy"]


def test_between_is_inclusive_at_both_ends():
    assert picked("age BETWEEN 7 AND 36") == ["ada", "cy"]
    assert picked("age BETWEEN 8 AND 35") == []


def test_the_bare_words_true_and_false():
    assert picked("TRUE") == ["ada", "bo", "cy", "di"]
    assert picked("FALSE") == []


def test_a_boolean_field_is_compared_against_a_boolean_value():
    assert picked("active = TRUE") == ["ada", "cy"]
    assert picked("active = FALSE") == ["bo", "di"]


def test_a_boolean_is_not_a_number():
    """`compare` says so and the module's own tests say so: True is not 1."""
    assert picked("active = 1") == []
    assert picked("active != 1") == ["ada", "bo", "cy", "di"]


def test_a_number_may_carry_a_minus_sign():
    records = [{"balance": -5}, {"balance": 5}]

    assert select(records, "balance = -5") == [records[0]]
    assert select(records, "balance < -1") == [records[0]]


def test_a_number_may_carry_a_decimal_point():
    records = [{"rate": 1.5}, {"rate": 2}]

    assert select(records, "rate = 1.5") == [records[0]]
    assert select(records, "rate > 1.75") == [records[1]]


def test_two_quotes_inside_a_text_literal_stand_for_one():
    records = [{"name": "o'brien"}, {"name": "obrien"}]

    assert select(records, "name = 'o''brien'") == [records[0]]


def test_a_text_literal_may_be_empty():
    records = [{"note": ""}, {"note": "x"}]

    assert select(records, "note = ''") == [records[0]]


# --- combining, and where it binds ---------------------------------------------


def test_and_and_or_and_not():
    assert picked("active = TRUE AND age > 10") == ["ada"]
    assert picked("age < 10 OR age > 50") == ["cy", "di"]
    assert picked("NOT city = 'york'") == ["cy"]


def test_not_binds_tighter_than_and():
    assert picked("NOT active = TRUE AND city = 'york'") == ["bo"]


def test_and_binds_tighter_than_or():
    assert picked("city = 'leeds' OR city = 'york' AND age > 10") == [
        "ada", "cy"]


def test_brackets_group():
    assert picked("(city = 'leeds' OR city = 'york') AND age > 10") == ["ada"]


def test_a_chain_of_ands_and_a_chain_of_ors():
    assert picked("age > 1 AND age < 100 AND city = 'york'") == ["ada"]
    assert picked("name = 'ada' OR name = 'bo' OR name = 'cy'") == [
        "ada", "bo", "cy"]


def test_not_may_be_written_twice():
    assert picked("NOT NOT city = 'york'") == ["ada", "bo"]


def test_keywords_may_be_written_in_any_case():
    assert picked("age is not null and city = 'york'") == ["ada"]
    assert picked("age Between 7 And 36") == ["ada", "cy"]


def test_whitespace_around_the_symbols_is_optional():
    assert picked("age>=36") == ["ada", "di"]
    assert picked("name IN('ada','cy')") == ["ada", "cy"]


# --- the unknown, which is the whole of the difficulty -------------------------


def test_a_comparison_against_the_unknown_selects_nothing():
    assert picked("age = 36") == ["ada"]
    assert "bo" not in picked("age != 36")


def test_not_leaves_the_unknown_alone():
    """Python's `not None` is True. `NOT UNKNOWN` is UNKNOWN, so bo is not
    selected by either the test or its negation."""
    assert "bo" not in picked("age > 10")
    assert "bo" not in picked("NOT age > 10")


def test_and_is_false_as_soon_as_one_part_is():
    """bo's age is unknown, so the first part is unknown; the second is
    false, and false and unknown is false rather than unknown — which makes
    no difference to what is selected, and every difference to its
    negation."""
    assert "bo" not in picked("age > 10 AND city = 'leeds'")
    assert "bo" in picked("NOT (age > 10 AND city = 'leeds')")


def test_or_is_true_as_soon_as_one_part_is():
    assert "bo" in picked("age > 10 OR city = 'york'")
    assert "bo" not in picked("age > 10 OR city = 'leeds'")


def test_an_unknown_or_an_unknown_stays_unknown():
    assert "bo" not in picked("age > 10 OR age <= 10")
    assert "bo" not in picked("NOT (age > 10 OR age <= 10)")


def test_in_is_unknown_rather_than_false_when_a_value_is_unknown():
    records = [{"n": 2}, {"n": 1}]

    assert select(records, "n IN (1, NULL)") == [records[1]]
    assert select(records, "NOT n IN (1, NULL)") == []


def test_in_is_plainly_false_when_no_value_is_unknown():
    records = [{"n": 2}, {"n": 1}]

    assert select(records, "NOT n IN (1, 3)") == [records[0]]


def test_between_follows_the_and_rule():
    records = [{"n": 1}, {"n": None}]

    assert select(records, "n BETWEEN 5 AND 10") == []
    assert select(records, "NOT n BETWEEN 5 AND 10") == [records[0]]


def test_comparing_against_the_word_null_is_unknown_not_a_match():
    assert picked("age = NULL") == []
    assert picked("age != NULL") == []


def test_a_field_a_record_does_not_carry_is_unknown_to_a_comparison():
    assert "di" not in picked("city = 'york'")
    assert "di" not in picked("city != 'york'")
    assert "di" not in picked("NOT city = 'york'")


# --- the refusals --------------------------------------------------------------


def test_a_field_no_record_carries_is_a_mistake():
    with pytest.raises(ValueError):
        select(PEOPLE, "nickname = 'x'")


def test_a_field_only_some_records_carry_is_not_a_mistake():
    assert picked("city = 'leeds'") == ["cy"]


def test_with_no_records_there_is_nothing_to_check_a_name_against():
    assert select([], "nickname = 'x'") == []


def test_an_unclosed_bracket():
    with pytest.raises(ValueError):
        select(PEOPLE, "(age > 1")


def test_an_unclosed_text_literal():
    with pytest.raises(ValueError):
        select(PEOPLE, "name = 'ada")


def test_a_missing_value():
    with pytest.raises(ValueError):
        select(PEOPLE, "age >")


def test_a_character_belonging_to_no_token():
    with pytest.raises(ValueError):
        select(PEOPLE, "age ~ 3")


def test_a_field_name_with_no_test_on_it():
    with pytest.raises(ValueError):
        select(PEOPLE, "age AND city = 'york'")


def test_something_trailing_after_the_expression_ends():
    with pytest.raises(ValueError):
        select(PEOPLE, "age > 1 city = 'york'")


def test_an_empty_expression():
    with pytest.raises(ValueError):
        select(PEOPLE, "")


def test_in_with_no_values():
    with pytest.raises(ValueError):
        select(PEOPLE, "name IN ()")


def test_is_followed_by_something_other_than_null():
    with pytest.raises(ValueError):
        select(PEOPLE, "age IS 3")


def test_between_without_its_and():
    with pytest.raises(ValueError):
        select(PEOPLE, "age BETWEEN 1 OR 2")


def test_an_ordering_compare_refuses_goes_on_being_refused():
    with pytest.raises(ValueError):
        select(PEOPLE, "age < 'x'")


def test_an_equality_across_two_kinds_is_false_and_not_a_refusal():
    assert picked("age = 'x'") == []
