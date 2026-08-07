from roll import Photo, describe, gaps, in_order, marked, shown

ROLL = [
    Photo(0, "heron", ""),
    Photo(1, "heron", "blurred"),
    Photo(3, "heron", "keep"),
    Photo(40, "reeds", ""),
    Photo(41, "reeds", ""),
]


def test_a_roll_taken_in_time_order_is_in_order():
    assert in_order(ROLL)


def test_a_roll_with_a_photo_out_of_its_place_is_not():
    assert not in_order([ROLL[3], ROLL[0]])


def test_two_photos_taken_at_the_same_second_are_still_in_order():
    assert in_order([Photo(5, "one", ""), Photo(5, "other", "")])


def test_an_empty_roll_is_in_order():
    assert in_order([])


def test_the_gaps_are_the_seconds_between_one_photo_and_the_next():
    assert gaps(ROLL) == [1, 2, 37, 1]


def test_a_single_photo_has_no_gaps():
    assert gaps(ROLL[:1]) == []


def test_the_photos_carrying_a_mark():
    assert shown(marked(ROLL, "blurred")) == ["heron"]
    assert shown(marked(ROLL, "keep")) == ["heron"]
    assert shown(marked(ROLL, "")) == ["heron", "reeds", "reeds"]


def test_nothing_carries_a_mark_nobody_used():
    assert marked(ROLL, "cropped") == []


def test_what_the_photos_show_comes_out_in_the_order_they_were_taken():
    assert shown(ROLL) == ["heron", "heron", "heron", "reeds", "reeds"]


def test_the_description_has_a_line_per_photo():
    assert describe(ROLL[:4]) == [
        "0s heron",
        "1s heron (blurred)",
        "3s heron (keep)",
        "40s reeds",
    ]
