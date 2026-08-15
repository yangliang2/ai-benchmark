from houses import House
from newsagent import Newsagent, counter_line
from rounds import Round
from tallying import Bundle

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


def shop():
    return Newsagent(MORNING, [Round(HERALD), Round(GAZETTE)])


def test_a_line_of_the_list_is_a_street_and_its_papers():
    assert counter_line(Bundle("mill lane", 2)) == "mill lane: 2"


def test_a_note_on_the_pad_is_written_in_beside_the_street():
    line = counter_line(Bundle("mill lane", 2), {"mill lane": "back door"})

    assert line == "mill lane: 2 (back door)"


def test_the_list_has_a_line_for_each_street_a_walk_takes_papers_in():
    made_up = shop().bundle_list(Round(HERALD))

    assert "mill lane: 2" in made_up
    assert "fen road: 1" in made_up


def test_a_note_reaches_the_list_the_counter_is_worked_from():
    made_up = shop().bundle_list(Round(HERALD), {"fen road": "no letterbox"})

    assert "fen road: 1 (no letterbox)" in made_up


def test_the_pad_by_the_till_is_not_written_to():
    notes = {"fen road": "no letterbox"}

    shop().bundle_list(Round(HERALD), notes)

    assert notes == {"fen road": "no letterbox"}


def test_every_round_is_counted_onto_one_list_walk_after_walk():
    assert shop().every_bundle() == [
        Bundle("fen road", 1),
        Bundle("mill lane", 2),
        Bundle("kiln row", 1),
        Bundle("mill lane", 1),
    ]


def test_a_shop_with_no_rounds_walked_out_of_it_counts_nothing():
    assert Newsagent(MORNING).every_bundle() == []


def test_how_many_a_walk_comes_to_leaves_out_the_streets_it_is_told_to():
    assert shop().how_many(Round(HERALD)) == 3
    assert shop().how_many(Round(HERALD), ["mill lane"]) == 1


def test_the_shop_makes_up_a_bag_for_every_forty_of_a_title():
    assert shop().papers_needed(HERALD) == 1
    assert shop().papers_needed("courier") == 0


def test_the_shop_walks_past_every_house_it_has():
    assert shop().walked_past() == [
        "1 fen road",
        "3 fen road",
        "5 kiln row",
        "2 mill lane",
        "4 mill lane",
        "6 mill lane",
    ]
