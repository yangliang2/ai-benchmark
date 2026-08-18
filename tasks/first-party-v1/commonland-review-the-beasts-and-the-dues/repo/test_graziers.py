from graziers import Beast, Grazier, Register


def test_the_commoners_come_back_in_the_order_the_stints_were_taken_up():
    register = Register()
    register.hold(Grazier("ada", 4))
    register.hold(Grazier("bob", 2))

    assert [grazier.who for grazier in register.graziers] == ["ada", "bob"]


def test_a_name_no_commoner_holds_a_stint_under_has_no_holder():
    register = Register()
    register.hold(Grazier("ada", 4))

    assert register.holder("ada").gates == 4
    assert register.holder("cid") is None


def test_a_beast_is_written_down_under_the_commoner_who_turned_it_out():
    register = Register()
    register.enter(Beast("ada", "cow", "AB"))
    register.enter(Beast("bob", "sheep", "CD"))

    assert [beast.mark for beast in register.beasts["ada"]] == ["AB"]


def test_the_register_takes_a_beast_the_stint_does_not_carry():
    register = Register()
    register.hold(Grazier("ada", 4))
    for mark in ("AB", "CD"):
        register.enter(Beast("ada", "horse", mark))

    assert [beast.mark for beast in register.beasts["ada"]] == ["AB", "CD"]
