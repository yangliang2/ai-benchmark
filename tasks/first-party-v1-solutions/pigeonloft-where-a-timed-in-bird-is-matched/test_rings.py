from rings import same_bird, tidy


def test_a_number_comes_back_without_its_spaces_and_in_capitals():
    assert tidy("gb 21 n 4471") == "GB21N4471"


def test_the_apostrophe_in_front_of_the_year_goes():
    assert tidy("GB'21N4471") == "GB21N4471"


def test_two_writings_of_one_number_are_the_one_bird():
    assert same_bird("gb 21 n 4471", "GB'21N4471")


def test_two_different_numbers_are_two_birds():
    assert not same_bird("GB21N4471", "GB21N4417")
