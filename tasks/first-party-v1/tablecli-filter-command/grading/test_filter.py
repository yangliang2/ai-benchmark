import pytest
from cli import main
from tabular import matches, parse

TEXT = """\
name,age,team
ada,36,red
grace,45,blue
alan,41,red
"""


def row(name):
    _, rows = parse(TEXT)
    [found] = [r for r in rows if r["name"] == name]
    return found


def test_equality_compares_cell_text():
    assert matches(row("ada"), "team=red")
    assert not matches(row("grace"), "team=red")


def test_inequality_compares_cell_text():
    assert matches(row("grace"), "team!=red")
    assert not matches(row("ada"), "team!=red")


def test_ordering_compares_numbers():
    assert matches(row("grace"), "age>41")
    assert not matches(row("alan"), "age>41")
    assert matches(row("ada"), "age<41")


def test_two_character_operators_are_not_misread():
    assert matches(row("alan"), "age>=41")
    assert matches(row("ada"), "age<=36")


def test_an_ordering_comparison_on_a_non_numeric_cell_raises():
    with pytest.raises(ValueError):
        matches(row("ada"), "name>10")


def test_an_unknown_column_is_named_in_the_error():
    with pytest.raises(ValueError, match="salary"):
        matches(row("ada"), "salary>10")


def test_a_condition_without_an_operator_raises():
    with pytest.raises(ValueError):
        matches(row("ada"), "age")


def test_the_filter_command_keeps_matching_rows_only():
    assert (
        main(["filter", "age>40"], TEXT)
        == "name,age,team\ngrace,45,blue\nalan,41,red"
    )


def test_several_conditions_must_all_hold():
    assert main(["filter", "age>40", "team=red"], TEXT) == "name,age,team\nalan,41,red"


def test_filter_without_conditions_raises():
    with pytest.raises(ValueError):
        main(["filter"], TEXT)


def test_existing_behaviour_is_preserved():
    assert main(["columns"], TEXT) == "name\nage\nteam"
    assert main(["count"], TEXT) == "3"
