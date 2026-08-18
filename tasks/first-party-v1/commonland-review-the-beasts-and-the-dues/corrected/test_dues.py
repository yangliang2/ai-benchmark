from dues import PENCE_A_GATE, reckoning
from graziers import Beast, Grazier, Register


def test_a_gate_is_thirty_pence():
    assert PENCE_A_GATE == 30


def test_the_one_commoner_on_the_common_pays_the_herdsman_between_them():
    register = Register()
    register.hold(Grazier("ada", 4))
    register.enter(Beast("ada", "cow", "AB"))

    assert reckoning(register, 60) == {"ada": 180}


def test_a_commoner_with_nothing_turned_out_owes_the_herdsman_nothing():
    register = Register()
    register.hold(Grazier("ada", 4))

    assert reckoning(register, 60) == {"ada": 0}
