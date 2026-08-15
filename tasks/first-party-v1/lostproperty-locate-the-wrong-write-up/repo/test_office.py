from handins import Handin
from office import Office, wording
from sorting import BINNED, RETURNED, SHELF

TODAY = 200

UMBRELLA = Handin("umbrella", 199)
COAT = Handin("coat", 40)
KEYS = Handin("keys", 190, claimed=True)


def test_a_verdict_is_written_up_in_words():
    assert wording(RETURNED) == "back to its owner"
    assert wording(BINNED) == "thrown out"
    assert wording(SHELF) == "on the shelf"


def test_the_book_gets_a_line_for_every_thing_the_office_held():
    office = Office([UMBRELLA, KEYS])
    assert office.written_up(TODAY) == [
        "keys: back to its owner",
        "umbrella: on the shelf",
    ]


def test_the_book_counts_what_it_put_under_each_verdict():
    counted = Office([UMBRELLA, COAT, KEYS]).counted(TODAY)
    assert counted == {"returned": 1, "binned": 0, "auction": 1, "shelf": 1}


def test_every_thing_the_office_holds_has_a_ticket_on_it():
    assert Office([UMBRELLA, KEYS]).tickets(TODAY) == [
        "keys - asked for",
        "umbrella - 1 days in",
    ]


def test_what_is_still_here_in_the_morning_is_what_was_not_settled_away():
    assert Office([UMBRELLA, COAT, KEYS]).still_here(TODAY) == [UMBRELLA]
