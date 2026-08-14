from passengers import Passenger, in_turn, waited_at_least

ADA = Passenger("Ada", 5)
BRAM = Passenger("Bram", 12)
CLARE = Passenger("Clare", 5)


def test_whoever_came_down_first_is_taken_first():
    assert in_turn([BRAM, ADA]) == [ADA, BRAM]


def test_two_who_came_down_together_keep_the_order_they_arrived_in():
    assert in_turn([BRAM, ADA, CLARE]) == [ADA, CLARE, BRAM]


def test_ordering_leaves_the_passengers_it_was_given_alone():
    given = [BRAM, ADA]
    in_turn(given)
    assert given == [BRAM, ADA]


def test_the_same_passenger_twice_is_one_passenger():
    assert {ADA, BRAM, Passenger("Ada", 5)} == {ADA, BRAM}


def test_a_passenger_says_who_they_are():
    assert repr(ADA) == "Passenger('Ada', 5)"


def test_a_passenger_who_has_sat_out_the_patience_is_counted():
    assert waited_at_least(ADA, 25)
    assert not waited_at_least(ADA, 24)
