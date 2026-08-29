from floor import Floor
from tape import Tape

CALLS = [("ten", 40), ("eleven", 35), ("noon", 50)]


def test_the_best_turn_buys_low_and_sells_later():
    assert Floor(Tape(CALLS)).best_turn() == ("eleven", "noon", 15)


def test_a_falling_day_offers_no_turn():
    assert Floor(Tape([("ten", 50), ("noon", 40)])).best_turn() is None


def test_the_tape_tallies_its_windings():
    tape = Tape(CALLS)

    assert tape.windings == 0
    assert tape.call_at(1) == ("eleven", 35)
    assert tape.windings == 1
