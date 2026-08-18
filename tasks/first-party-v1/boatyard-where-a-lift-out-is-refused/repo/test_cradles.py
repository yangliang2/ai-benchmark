from cradles import Cradle, cradle_for


def test_a_frame_takes_a_hull_up_to_its_pattern_and_no_wider():
    frame = Cradle("medium")

    assert frame.takes(330)
    assert not frame.takes(331)


def test_the_slightest_frame_that_fits_is_the_one_picked():
    frames = [Cradle("heavy"), Cradle("medium"), Cradle("light")]

    assert cradle_for(frames, 200).pattern == "light"
    assert cradle_for(frames, 300).pattern == "medium"
    assert cradle_for(frames, 400).pattern == "heavy"


def test_a_frame_with_something_on_it_is_not_free():
    frames = [Cradle("light", holding="Kittiwake"), Cradle("medium")]

    assert cradle_for(frames, 200).pattern == "medium"


def test_nothing_wide_enough_gives_nothing_back():
    assert cradle_for([Cradle("light")], 500) is None


def test_an_unknown_pattern_is_refused_outright():
    try:
        Cradle("enormous")
    except ValueError as error:
        assert "enormous" in str(error)
    else:
        raise AssertionError("an unknown pattern should not make a frame")
