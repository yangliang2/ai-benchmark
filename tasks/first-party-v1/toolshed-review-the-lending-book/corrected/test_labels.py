from labels import tidy


def test_a_label_comes_out_the_same_however_it_was_put_in():
    assert tidy("  Long Bar   Clamp ") == "long bar clamp"


def test_a_label_that_is_already_down_that_way_is_left_alone():
    assert tidy("hand saw") == "hand saw"
