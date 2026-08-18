from hall import Room, big_enough, named


def rooms():
    return [Room("big", 80, 900), Room("small", 20, 400)]


def test_a_room_is_the_one_of_that_name_in_the_list():
    assert named(rooms(), "small").seats == 20


def test_a_room_the_hall_has_not_got_is_no_room_at_all():
    assert named(rooms(), "cellar") is None


def test_every_room_that_seats_a_party_comes_out_in_name_order():
    assert big_enough(rooms(), 20) == ["big", "small"]


def test_a_room_too_small_for_a_party_is_left_out():
    assert big_enough(rooms(), 50) == ["big"]
