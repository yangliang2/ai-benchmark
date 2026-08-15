"""Held out: what the shop answers when it is asked more than once."""

from houses import House, address, in_order, taking
from newsagent import Newsagent, counter_line
from rounds import Bag, Round, bagfuls
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

# What each walk comes to on its own, a street at a time and in walk order.
HERALD_BUNDLES = [Bundle("fen road", 1), Bundle("mill lane", 2)]
GAZETTE_BUNDLES = [Bundle("kiln row", 1), Bundle("mill lane", 1)]


def shop():
    return Newsagent(MORNING, [Round(HERALD), Round(GAZETTE)])


def test_one_ask_comes_back_as_the_walk_it_asked_about():
    assert Slate(MORNING).bundles(Round(HERALD)) == HERALD_BUNDLES


def test_a_second_ask_carries_nothing_of_the_first():
    slate = Slate(MORNING)

    slate.bundles(Round(HERALD))

    assert slate.bundles(Round(GAZETTE)) == GAZETTE_BUNDLES


def test_asking_the_same_thing_twice_answers_the_same_twice():
    slate = Slate(MORNING)

    assert slate.bundles(Round(HERALD)) == HERALD_BUNDLES
    assert slate.bundles(Round(HERALD)) == HERALD_BUNDLES


def test_a_slate_the_shop_has_never_used_starts_with_nothing_on_it():
    Slate(MORNING).bundles(Round(HERALD))

    assert Slate(MORNING).bundles(Round(GAZETTE)) == GAZETTE_BUNDLES


def test_the_list_the_counter_is_worked_from_is_one_walk_at_a_time():
    counter = shop()

    assert counter.bundle_list(Round(HERALD)) == ["fen road: 1", "mill lane: 2"]
    assert counter.bundle_list(Round(GAZETTE)) == ["kiln row: 1", "mill lane: 1"]
    assert counter.bundle_list(Round(HERALD)) == ["fen road: 1", "mill lane: 2"]


def test_a_walk_nobody_takes_comes_back_with_nothing_on_it():
    slate = Slate(MORNING)

    slate.bundles(Round(HERALD))

    assert slate.bundles(Round("courier")) == []


def test_a_count_put_in_is_added_to_and_comes_back():
    """What the parameter is for, and what the fix must leave alone: a count
    handed to the slate is the one added to, in place, and handed back."""
    begun = [Bundle("brick hill", 5)]

    counted = Slate(MORNING).bundles(Round(HERALD), begun)

    assert counted is begun
    assert begun == [Bundle("brick hill", 5), *HERALD_BUNDLES]


def test_every_round_is_still_counted_onto_one_list():
    assert shop().every_bundle() == HERALD_BUNDLES + GAZETTE_BUNDLES


def test_the_busiest_street_is_still_the_one_taking_the_most():
    slate = Slate(MORNING)

    slate.bundles(Round(GAZETTE))

    assert slate.busiest(Round(HERALD)) == Bundle("mill lane", 2)
    assert slate.busiest(Round("courier")) is None


def test_how_many_a_walk_comes_to_is_still_that_walk():
    counter = shop()

    counter.bundle_list(Round(HERALD))

    assert counter.how_many(Round(GAZETTE)) == 2
    assert counter.how_many(Round(GAZETTE), ["mill lane"]) == 1


def test_the_neighbouring_reckonings_are_unchanged():
    """What the fix must leave alone: the order a walk goes in, which houses
    it drops at, what it carries, and the words a line is written in."""
    walk = Round(HERALD, ["mill lane"])

    assert [address(house) for house in walk.drops(MORNING)] == [
        "2 mill lane",
        "6 mill lane",
        "1 fen road",
    ]
    assert [address(house) for house in Round(HERALD).drops(MORNING, [2])] == [
        "1 fen road",
        "6 mill lane",
    ]
    assert Round(HERALD).bagful(MORNING) == Bag(3, 1)
    assert bagfuls(41) == 2
    assert Bag(3, 1).room_left() == 37
    assert [address(house) for house in in_order(MORNING)][0] == "1 fen road"
    assert taking(MORNING, GAZETTE) == [
        House(4, "mill lane", GAZETTE),
        House(5, "kiln row", GAZETTE),
    ]
    assert added_up(HERALD_BUNDLES) == 3
    assert added_up(HERALD_BUNDLES, ["mill lane"]) == 1
    assert counter_line(Bundle("mill lane", 2), {"mill lane": "back door"}) == (
        "mill lane: 2 (back door)"
    )
    assert shop().papers_needed(HERALD) == 1
    assert shop().walked_past()[0] == "1 fen road"
