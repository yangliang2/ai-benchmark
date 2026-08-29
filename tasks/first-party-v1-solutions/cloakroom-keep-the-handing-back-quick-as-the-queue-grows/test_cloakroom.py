from cloakroom import Cloakroom
from pegs import Coat, Rail

COATS = [
    Coat(31, "green ulster"),
    Coat(7, "grey mackintosh"),
    Coat(52, "brown greatcoat"),
]


def test_each_ticket_gets_its_own_coat():
    room = Cloakroom(Rail(COATS))

    assert room.hand_back([52, 31]) == [
        (52, "brown greatcoat"),
        (31, "green ulster"),
    ]


def test_a_ticket_no_coat_carries_is_refused():
    assert Cloakroom(Rail(COATS)).coat_for(99) is None


def test_the_rail_tallies_its_take_downs():
    rail = Rail(COATS)

    assert rail.takedowns == 0
    assert rail.take_down(1).ticket == 7
    assert rail.takedowns == 1
