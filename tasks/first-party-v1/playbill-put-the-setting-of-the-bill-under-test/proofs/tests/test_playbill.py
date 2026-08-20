"""The author's reference suite for the setting of the playbill.

The task's registered existence proof: the suite a perfect agent would have
written, at the shape the prompt asks for — `test_*.py` under `tests/`,
standing on its own, no conftest.py and no helper module beside it. The lint
runs it against the pristine repository and against each planted behaviour
change in turn, which is what says the task is solvable exactly as written.

Never overlaid into a workdir, never collected by a verdict: it lives here,
beside repo/, where every action's existence proof lives.
"""

import pytest

from playbill import centre, set_bill


# --- the words and the lines they are set into ---------------------------------


def test_a_text_narrower_than_the_measure_is_one_line():
    assert set_bill("a night of song", 20) == ["a night of song"]


def test_the_words_are_set_in_the_order_they_were_written():
    lines = set_bill("the tumblers and the tightrope and the tank", 12)

    assert " ".join(lines) == "the tumblers and the tightrope and the tank"


def test_a_line_is_broken_at_the_last_word_that_fits():
    assert set_bill("the great malini appears", 16) == [
        "the great malini",
        "appears",
    ]


def test_a_word_that_fills_the_measure_exactly_stays_on_the_line():
    # "one two" is seven characters, the measure exactly.
    assert set_bill("one two three", 7) == ["one two", "three"]


def test_a_word_one_character_too_long_for_the_line_starts_the_next():
    assert set_bill("one two three", 6) == ["one", "two", "three"]


def test_the_space_between_two_words_is_counted_in_the_measure():
    # "ab cd" is five characters; at four, only "ab" fits the first line.
    assert set_bill("ab cd", 4) == ["ab", "cd"]
    assert set_bill("ab cd", 5) == ["ab cd"]


def test_a_word_wider_than_the_measure_stands_on_a_line_of_its_own():
    assert set_bill("see the prestidigitator now", 10) == [
        "see the",
        "prestidigitator",
        "now",
    ]


def test_a_measure_of_one_gives_a_line_to_every_word():
    assert set_bill("song and dance", 1) == ["song", "and", "dance"]


def test_a_run_of_whitespace_between_words_is_one_parting():
    assert set_bill("the   band\tplays\non", 40) == ["the band plays on"]


def test_a_text_of_nothing_but_whitespace_sets_no_lines():
    assert set_bill("", 20) == []
    assert set_bill("   \t\n ", 20) == []


def test_no_line_carries_a_space_at_either_end():
    for line in set_bill("  a   night   of   song  ", 9):
        assert line == line.strip()
        assert "  " not in line


def test_a_measure_of_less_than_one_character_sets_nothing_at_all():
    with pytest.raises(ValueError):
        set_bill("a night of song", 0)
    with pytest.raises(ValueError):
        set_bill("a night of song", -3)


# --- a line stood in the middle of the measure ---------------------------------


def test_a_line_is_stood_in_the_middle_by_the_space_before_it():
    assert centre("song", 10) == "   song"


def test_a_line_that_cannot_be_halved_evenly_leans_to_the_left():
    # Five characters spare, so two before it rather than three.
    assert centre("song", 9) == "  song"


def test_a_line_the_width_of_the_measure_is_left_where_it_is():
    assert centre("song", 4) == "song"


def test_a_line_wider_than_the_measure_is_left_where_it_is():
    assert centre("prestidigitator", 8) == "prestidigitator"


def test_a_centred_line_carries_no_space_after_it():
    assert centre("song", 12) == "    song"
    assert not centre("song", 12).endswith(" ")


def test_centring_to_less_than_one_character_is_an_error():
    with pytest.raises(ValueError):
        centre("song", 0)
    with pytest.raises(ValueError):
        centre("song", -2)
