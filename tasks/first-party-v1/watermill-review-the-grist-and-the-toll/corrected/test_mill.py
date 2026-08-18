from mill import (
    FLOORS,
    Leat,
    Stones,
    bushels,
    floors_in_use,
    on_the_floor,
    sacks_to_carry,
    turning,
)


def test_a_pair_of_stones_is_found_however_the_name_was_written_down():
    stones = [Stones("Blue Peak", "the stone floor", 8)]

    assert turning(stones, " blue peak ").furrows == 8
    assert turning(stones, "French Burr") is None


def test_the_pairs_of_one_floor_come_back_in_the_order_they_were_put_in():
    stones = [
        Stones("Blue Peak", "the stone floor", 8),
        Stones("French Burr", "the meal floor", 10),
        Stones("Grey Buhr", "the stone floor", 8),
    ]

    assert [pair.name for pair in on_the_floor(stones, "the stone floor")] == [
        "Blue Peak",
        "Grey Buhr",
    ]
    assert floors_in_use(stones) == 2


def test_the_leat_says_what_it_comes_down_with():
    leat = Leat("the glebe", 9)

    assert (leat.whose, leat.fall) == ("the glebe", 9)
    assert FLOORS[0] == "the bin floor"


def test_what_will_not_fill_a_bushel_is_not_a_bushel():
    assert bushels(9) == 2
    assert bushels(3) == 0


def test_a_lot_part_filling_a_sack_still_takes_a_sack_to_carry_it():
    assert sacks_to_carry(9) == 2
    assert sacks_to_carry(16) == 2
    assert sacks_to_carry(0) == 0
