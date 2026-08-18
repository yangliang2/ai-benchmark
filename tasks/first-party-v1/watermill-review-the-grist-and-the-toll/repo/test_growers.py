from growers import Grower, Round


def test_the_round_holds_its_growers_in_the_order_they_came_on():
    round_ = Round()
    round_.come_on(Grower("hale", "Barrow End"))
    round_.come_on(Grower("dray", "Long Meadow"))

    assert [grower.who for grower in round_.growers] == ["hale", "dray"]


def test_the_round_puts_a_second_of_one_name_on_as_it_is_given():
    round_ = Round()
    round_.come_on(Grower("hale", "Barrow End"))
    round_.come_on(Grower("hale", "Pightle"))

    assert [grower.farm for grower in round_.growers] == ["Barrow End", "Pightle"]


def test_a_grower_is_found_however_their_name_was_written_down():
    round_ = Round()
    round_.come_on(Grower("Amos Hale", "Barrow End"))

    assert round_.grower(" amos hale ").farm == "Barrow End"
    assert round_.grower("dray") is None


def test_two_growers_off_the_one_farm_are_off_the_one_farm():
    round_ = Round()
    round_.come_on(Grower("hale", "Barrow End"))
    round_.come_on(Grower("dray", "Long Meadow"))
    round_.come_on(Grower("wick", "Barrow End"))

    assert round_.farms() == ["Barrow End", "Long Meadow"]
