import pytest

from gradebook import summary


def test_summary_of_an_odd_class():
    assert summary([70, 91, 80]) == (
        "students: 3\naverage: 80.3\nmedian: 80.0\nbest: 91\nworst: 70"
    )


def test_summary_of_an_even_class():
    assert summary([60, 90]) == (
        "students: 2\naverage: 75.0\nmedian: 75.0\nbest: 90\nworst: 60"
    )


def test_an_empty_gradebook_is_rejected():
    with pytest.raises(ValueError, match="no scores to summarise"):
        summary([])
