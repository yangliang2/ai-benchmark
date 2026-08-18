from rota import is_open, whose_turn


def test_the_doors_are_open_on_the_two_afternoons_they_are_open_on():
    assert is_open("Tuesday")
    assert is_open(" saturday ")
    assert not is_open("monday")


def test_the_turn_goes_round_the_volunteers_in_the_order_they_are_listed():
    volunteers = ["ada", "bob", "cyd"]

    assert whose_turn(volunteers, 0) == "ada"
    assert whose_turn(volunteers, 4) == "bob"
