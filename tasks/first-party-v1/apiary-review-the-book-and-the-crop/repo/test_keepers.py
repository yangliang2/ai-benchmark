from keepers import Keeper, Roll


def test_the_roll_holds_its_members_in_the_order_they_joined():
    roll = Roll()
    roll.join(Keeper("ann", ["WB2"]))
    roll.join(Keeper("bea", ["WB5"]))

    assert [keeper.who for keeper in roll.keepers] == ["ann", "bea"]


def test_the_roll_puts_a_second_of_one_name_on_as_it_is_given():
    roll = Roll()
    roll.join(Keeper("ann", ["WB2"]))
    roll.join(Keeper("ann", ["WB7"]))

    assert [keeper.hives for keeper in roll.keepers] == [["WB2"], ["WB7"]]


def test_a_member_is_found_however_their_name_was_written_down():
    roll = Roll()
    roll.join(Keeper("Ann Fisk", ["WB2"]))

    assert roll.member(" ann fisk ").hives == ["WB2"]
    assert roll.member("cal") is None


def test_a_hive_kept_between_two_members_is_kept_by_both_of_them():
    roll = Roll()
    roll.join(Keeper("ann", ["WB2", "WB5"]))
    roll.join(Keeper("bea", ["WB2"]))

    assert [keeper.who for keeper in roll.keeping("WB2")] == ["ann", "bea"]
    assert [keeper.who for keeper in roll.keeping("WB5")] == ["ann"]
