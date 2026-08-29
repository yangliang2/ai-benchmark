"""Behaviour half of the grading suite: correctness, unchanged.

Must pass on the pristine repository and on the reference solution — the
handing back is already right, and "stay quick" preserves it. Nothing here
reads the take-down tally: what the change may not alter is what the queue
is told, and that is all this half asserts.
"""

from cloakroom import Cloakroom
from pegs import Coat, Rail


def a_room(*spec):
    return Cloakroom(Rail([Coat(ticket, coat) for ticket, coat in spec]))


WARDROBE = (
    (14, "green ulster"),
    (3, "grey mackintosh"),
    (27, "brown greatcoat"),
    (8, "blue cape"),
    (41, "black opera cloak"),
)


def test_each_ticket_gets_the_coat_checked_under_it():
    room = a_room(*WARDROBE)

    assert room.hand_back([27, 8, 14]) == [
        (27, "brown greatcoat"),
        (8, "blue cape"),
        (14, "green ulster"),
    ]


def test_a_ticket_no_coat_carries_is_refused():
    room = a_room(*WARDROBE)

    assert room.coat_for(99) is None
    assert room.hand_back([99, 3]) == [(99, None), (3, "grey mackintosh")]


def test_the_queue_is_answered_in_the_order_it_formed():
    room = a_room(*WARDROBE)

    assert room.hand_back([41, 3, 8]) == [
        (41, "black opera cloak"),
        (3, "grey mackintosh"),
        (8, "blue cape"),
    ]


def test_an_asking_repeated_is_answered_the_same_way():
    room = a_room(*WARDROBE)

    assert room.hand_back([8, 8]) == [(8, "blue cape"), (8, "blue cape")]


def test_an_empty_queue_is_answered_with_nothing():
    assert a_room(*WARDROBE).hand_back([]) == []


def test_an_empty_rail_refuses_every_ticket():
    assert a_room().hand_back([14]) == [(14, None)]


def test_coat_for_agrees_with_the_hand_back():
    room = a_room(*WARDROBE)

    assert room.coat_for(3) == "grey mackintosh"
    assert room.hand_back([3]) == [(3, "grey mackintosh")]
