from entries import Entries, Entry, Race

FRAISTHORPE = Race("Fraisthorpe", "08:00", "19:30")
BERWICK = Race("Berwick", "07:30", "20:00")

SHEETS = Entries([
    Entry(FRAISTHORPE, "Ackroyd", "GB21N4471"),
    Entry(BERWICK, "Ackroyd", "GB21N4471"),
    Entry(FRAISTHORPE, "Wilbraham", "GB 22 N 118"),
    Entry(FRAISTHORPE, "Ackroyd", "gb21n4471"),
])


def test_only_that_race_comes_back_and_in_the_order_taken_down():
    assert [entry.loft for entry in SHEETS.for_race(FRAISTHORPE)] == [
        "Ackroyd", "Wilbraham", "Ackroyd",
    ]


def test_a_race_no_member_entered_comes_back_bare():
    assert SHEETS.for_race(Race("Thurso", "05:00", "21:00")) == []


def test_a_loft_gets_back_everything_it_entered():
    assert [entry.race.name for entry in SHEETS.by_loft("Wilbraham")] == [
        "Fraisthorpe",
    ]


def test_a_race_is_open_between_the_two_hours_it_was_made_with():
    assert (FRAISTHORPE.opens, FRAISTHORPE.shuts) == ("08:00", "19:30")
