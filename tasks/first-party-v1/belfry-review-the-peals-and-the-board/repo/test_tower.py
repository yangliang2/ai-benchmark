from tower import BELLS, Bell, Frame, heaviest_first, hung, minutes


def test_a_peal_stood_from_the_stroke_pulled_off_at_to_the_one_it_came_round_at():
    assert minutes(600, 780) == 180


def test_the_bells_ring_down_with_the_heaviest_at_the_head():
    bells = [Bell("treble", 5), Bell("tenor", 21), Bell("third", 8)]

    rung_down = [bell.called for bell in heaviest_first(bells)]

    assert rung_down == ["tenor", "third", "treble"]


def test_a_bell_is_found_however_the_name_it_hangs_under_was_written():
    bells = [Bell("Tenor", 21)]

    assert hung(bells, " tenor ").hundredweight == 21
    assert hung(bells, "second") is None


def test_the_frame_says_what_it_was_built_with():
    frame = Frame("St Botolph", 8)

    assert (frame.where, frame.pits) == ("St Botolph", 8)
    assert BELLS[0] == "treble"
