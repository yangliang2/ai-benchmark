from houses import House, address
from rounds import PAPERS_A_BAG_HOLDS, Bag, Round, bagfuls

HERALD = "herald"
GAZETTE = "gazette"

MORNING = [
    House(2, "mill lane", HERALD),
    House(4, "mill lane", GAZETTE),
    House(6, "mill lane", HERALD),
    House(1, "fen road", HERALD),
    House(3, "fen road"),
    House(5, "kiln row", GAZETTE),
]


def test_a_walk_drops_at_the_houses_taking_its_title():
    dropped = Round(HERALD).drops(MORNING)

    assert [address(house) for house in dropped] == [
        "1 fen road",
        "2 mill lane",
        "6 mill lane",
    ]


def test_a_walk_takes_the_streets_in_the_order_it_is_walked_in():
    dropped = Round(HERALD, ["mill lane"]).drops(MORNING)

    assert [address(house) for house in dropped] == [
        "2 mill lane",
        "6 mill lane",
        "1 fen road",
    ]


def test_a_number_left_off_this_week_is_walked_past():
    dropped = Round(HERALD).drops(MORNING, [2, 6])

    assert [address(house) for house in dropped] == ["1 fen road"]


def test_the_numbers_left_off_are_not_added_to():
    skipping = [2]

    Round(HERALD).drops(MORNING, skipping)

    assert skipping == [2]


def test_a_house_taking_nothing_is_on_nobody_s_walk():
    assert not Round(HERALD).takes(House(3, "fen road"))
    assert not Round(GAZETTE).takes(House(3, "fen road"))


def test_a_walk_carries_a_bag_for_every_forty_papers():
    assert bagfuls(1) == 1
    assert bagfuls(PAPERS_A_BAG_HOLDS) == 1
    assert bagfuls(PAPERS_A_BAG_HOLDS + 1) == 2


def test_nothing_to_carry_is_no_bag_to_carry_it_in():
    assert bagfuls(0) == 0


def test_a_bagful_is_the_papers_dropped_and_the_bags_they_go_in():
    assert Round(HERALD).bagful(MORNING) == Bag(3, 1)
    assert Round("courier").bagful(MORNING) == Bag(0, 0)


def test_a_bag_says_how_much_room_is_left_in_it():
    assert Bag(3, 1).room_left() == PAPERS_A_BAG_HOLDS - 3
    assert Bag(PAPERS_A_BAG_HOLDS, 1).room_left() == 0
