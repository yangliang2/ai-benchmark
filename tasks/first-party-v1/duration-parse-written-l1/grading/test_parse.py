import pytest
from duration import format_duration, parse, unit_seconds


def test_one_part_is_its_own_count_of_seconds():
    assert parse("90s") == 90


def test_the_parts_add_up():
    assert parse("1h 30m") == 5400


def test_every_unit_is_understood():
    assert parse("1w 2d 3h 4m 5s") == 604800 + 2 * 86400 + 3 * 3600 + 4 * 60 + 5


def test_units_are_read_without_regard_to_case():
    assert parse("1H 30M") == 5400


def test_the_spaces_between_parts_are_optional():
    assert parse("1h30m") == 5400


def test_space_around_and_between_the_parts_is_ignored():
    assert parse("  1h   30m  ") == 5400


def test_a_count_need_not_fit_inside_its_own_unit():
    assert parse("90m") == 5400


def test_zero_seconds_is_a_duration():
    assert parse("0s") == 0


def test_what_format_duration_writes_reads_back_as_what_it_was_given():
    for seconds in (0, 1, 59, 60, 3599, 3600, 5400, 90061, 1234567):
        assert parse(format_duration(seconds)) == seconds


def test_units_out_of_order_are_not_a_duration():
    with pytest.raises(ValueError):
        parse("30m 1h")


def test_a_unit_used_twice_is_not_a_duration():
    with pytest.raises(ValueError):
        parse("1h 2h")


def test_a_count_with_no_unit_is_not_a_duration():
    with pytest.raises(ValueError):
        parse("90")


def test_a_unit_with_no_count_is_not_a_duration():
    with pytest.raises(ValueError):
        parse("h")


def test_a_unit_the_module_does_not_know_is_not_a_duration():
    with pytest.raises(ValueError):
        parse("1y")


def test_nothing_at_all_is_not_a_duration():
    with pytest.raises(ValueError):
        parse("")


def test_the_existing_behaviour_is_preserved():
    assert format_duration(5400) == "1h 30m"
    assert format_duration(0) == "0s"
    assert unit_seconds("D") == 86400
