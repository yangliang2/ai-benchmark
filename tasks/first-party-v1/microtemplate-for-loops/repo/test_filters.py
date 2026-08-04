from filters import FILTERS


def test_upper_uppercases():
    assert FILTERS["upper"]("ada") == "ADA"


def test_lower_lowercases():
    assert FILTERS["lower"]("ADA") == "ada"
