from houses import NO_PAPER, House, address, in_order, taking

HERALD = "herald"
GAZETTE = "gazette"

MILL_LANE = [
    House(2, "mill lane", HERALD),
    House(4, "mill lane", GAZETTE),
    House(6, "mill lane", HERALD),
]
FEN_ROAD = [House(1, "fen road", HERALD), House(3, "fen road")]
KILN_ROW = [House(5, "kiln row", GAZETTE)]

MORNING = MILL_LANE + FEN_ROAD + KILN_ROW


def test_an_address_is_the_number_and_then_the_street():
    assert address(House(2, "mill lane", HERALD)) == "2 mill lane"


def test_a_house_takes_nothing_unless_it_is_said_to():
    assert House(3, "fen road").takes is NO_PAPER


def test_two_houses_with_the_same_of_everything_are_the_same_house():
    assert House(2, "mill lane", HERALD) == House(2, "mill lane", HERALD)
    assert House(2, "mill lane", HERALD) != House(2, "mill lane", GAZETTE)


def test_the_streets_come_alphabetically_and_the_numbers_go_up():
    assert [address(house) for house in in_order(MORNING)] == [
        "1 fen road",
        "3 fen road",
        "5 kiln row",
        "2 mill lane",
        "4 mill lane",
        "6 mill lane",
    ]


def test_a_street_the_shop_has_written_down_comes_first():
    assert [address(house) for house in in_order(MORNING, ["mill lane"])] == [
        "2 mill lane",
        "4 mill lane",
        "6 mill lane",
        "1 fen road",
        "3 fen road",
        "5 kiln row",
    ]


def test_the_order_the_shop_wrote_down_is_not_added_to():
    streets = ["mill lane"]

    in_order(MORNING, streets)

    assert streets == ["mill lane"]


def test_the_houses_taking_one_title_are_the_ones_that_take_it():
    assert taking(MORNING, GAZETTE) == [
        House(4, "mill lane", GAZETTE),
        House(5, "kiln row", GAZETTE),
    ]
