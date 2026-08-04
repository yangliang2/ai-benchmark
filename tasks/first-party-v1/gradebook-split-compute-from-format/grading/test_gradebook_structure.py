"""Structural half of the grading suite: asserts the two halves exist on
their own. Fails on the pristine repo, where neither function exists."""

import inspect

import gradebook
import pytest
from gradebook import compute_stats, format_summary


def test_compute_stats_returns_numbers_not_text():
    assert compute_stats([70, 80, 90]) == {
        "count": 3, "mean": 80.0, "median": 80.0, "best": 90, "worst": 70,
    }
    assert compute_stats([60, 90]) == {
        "count": 2, "mean": 75.0, "median": 75.0, "best": 90, "worst": 60,
    }


def test_compute_stats_owns_the_empty_gradebook_error():
    with pytest.raises(ValueError, match="no scores to summarise"):
        compute_stats([])


def test_format_summary_renders_what_it_is_given():
    # Deliberately inconsistent numbers: a format_summary that recomputes
    # from scores cannot produce this block, only a pure renderer can.
    stats = {"count": 9, "mean": 41.25, "median": 2.0, "best": 3, "worst": 3}

    assert format_summary(stats) == (
        "students: 9\naverage: 41.2\nmedian: 2.0\nbest: 3\nworst: 3"
    )


def test_summary_is_a_composition_of_the_two():
    source = inspect.getsource(gradebook.summary)
    assert "compute_stats" in source
    assert "format_summary" in source
    # The format literal lives in format_summary alone.
    assert inspect.getsource(gradebook).count("students:") == 1
