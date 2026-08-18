from clocking import Book, Clocked
from entries import Entries, Entry, Race

FRAISTHORPE = Race("Fraisthorpe", "08:00", "19:30")
BERWICK = Race("Berwick", "07:30", "20:00")

ACKROYD_FIRST = Entry(FRAISTHORPE, "Ackroyd", "GB21N4471")
ACKROYD_AGAIN = Entry(FRAISTHORPE, "Ackroyd", "gb 21 n 4471")

BOOK = Book(Entries([
    ACKROYD_FIRST,
    Entry(FRAISTHORPE, "Wilbraham", "GB22N118"),
    ACKROYD_AGAIN,
    Entry(BERWICK, "Ackroyd", "GB21N4471"),
]))


def test_a_bird_counts_for_the_line_its_own_loft_entered():
    clocked = Clocked("gb 21 n 4471", "Ackroyd", "16:20")

    assert BOOK.belongs_to(clocked, FRAISTHORPE) is ACKROYD_FIRST


def test_the_number_is_taken_as_it_was_given():
    assert BOOK.belongs_to(Clocked("GB'22N118", "Wilbraham", "17:00"), FRAISTHORPE)


def test_a_number_another_loft_entered_is_not_this_lofts_bird():
    assert BOOK.belongs_to(Clocked("GB21N4471", "Wilbraham", "16:20"), FRAISTHORPE) is None


def test_a_bird_timed_before_the_race_is_open_counts_for_nothing():
    assert BOOK.belongs_to(Clocked("GB21N4471", "Ackroyd", "07:55"), FRAISTHORPE) is None


def test_a_bird_timed_after_the_race_has_closed_counts_for_nothing():
    assert BOOK.belongs_to(Clocked("GB21N4471", "Ackroyd", "19:31"), FRAISTHORPE) is None


def test_a_number_no_loft_entered_counts_for_nothing():
    assert BOOK.belongs_to(Clocked("GB19N7", "Ackroyd", "16:20"), FRAISTHORPE) is None


def test_a_line_of_another_race_is_not_a_line_of_this_one():
    assert BOOK.belongs_to(Clocked("GB21N4471", "Ackroyd", "16:20"), BERWICK).race is BERWICK


def test_the_birds_that_count_for_no_line_come_back_in_a_lump():
    timed_in = [
        Clocked("GB21N4471", "Ackroyd", "16:20"),
        Clocked("GB19N7", "Ackroyd", "16:25"),
        Clocked("GB22N118", "Wilbraham", "21:00"),
    ]

    assert [bird.ring for bird in BOOK.unaccounted(timed_in, FRAISTHORPE)] == [
        "GB19N7", "GB22N118",
    ]
