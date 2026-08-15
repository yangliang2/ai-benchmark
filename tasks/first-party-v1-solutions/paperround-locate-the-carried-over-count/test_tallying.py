from houses import House, address
from rounds import Round
from tallying import Bundle, Slate, added_up

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


def test_the_slate_walks_a_round_in_the_order_it_takes_the_houses():
    walked = Slate(MORNING).walked(Round(GAZETTE))

    assert [address(house) for house in walked] == ["5 kiln row", "4 mill lane"]


def test_a_walk_is_tied_into_a_bundle_a_street():
    counted = Slate(MORNING).bundles(Round(HERALD))

    assert Bundle("mill lane", 2) in counted
    assert Bundle("fen road", 1) in counted


def test_a_house_taking_another_title_is_not_in_the_bundle():
    counted = Slate(MORNING).bundles(Round(GAZETTE))

    assert Bundle("mill lane", 1) in counted


def test_a_count_already_begun_is_added_to_and_comes_back():
    begun = [Bundle("brick hill", 5)]

    counted = Slate(MORNING).bundles(Round(HERALD), begun)

    assert counted is begun
    assert Bundle("brick hill", 5) in counted
    assert Bundle("mill lane", 2) in counted


def test_the_busiest_street_is_the_one_taking_the_most_papers():
    assert Slate(MORNING).busiest(Round(HERALD)) == Bundle("mill lane", 2)


def test_a_walk_that_drops_nothing_has_no_busiest_street():
    assert Slate(MORNING).busiest(Round("courier")) is None


def test_bundles_add_up_to_the_papers_in_them():
    assert added_up([Bundle("mill lane", 2), Bundle("fen road", 1)]) == 3


def test_nothing_at_all_adds_up_to_nothing():
    assert added_up([]) == 0


def test_a_street_left_out_of_the_reckoning_is_not_added_up():
    bundles = [Bundle("mill lane", 2), Bundle("fen road", 1)]

    assert added_up(bundles, ["mill lane"]) == 1
