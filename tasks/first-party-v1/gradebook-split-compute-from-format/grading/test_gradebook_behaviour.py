"""Behaviour half of the grading suite: must pass before and after the
split, so it pins summary's rendered block and error only."""

import pytest
from gradebook import summary


def test_summary_of_an_odd_class():
    assert summary([70, 91, 80]) == (
        "students: 3\naverage: 80.3\nmedian: 80.0\nbest: 91\nworst: 70"
    )


def test_summary_of_an_even_class_averages_the_middle_pair():
    assert summary([60, 90, 70, 100]) == (
        "students: 4\naverage: 80.0\nmedian: 80.0\nbest: 100\nworst: 60"
    )


def test_summary_of_a_single_score():
    assert summary([85]) == (
        "students: 1\naverage: 85.0\nmedian: 85.0\nbest: 85\nworst: 85"
    )


def test_an_empty_gradebook_is_rejected():
    with pytest.raises(ValueError, match="no scores to summarise"):
        summary([])
