from bands import Band
from diary import Booking, Diary

FERRYMEN = Band("The Ferrymen", 8)
SILVER = Band("Silver Prize", 24)

DIARY = Diary([
    Booking("06-14", SILVER, "4pm", 45),
    Booking("06-07", FERRYMEN, "3pm", 45),
    Booking("06-14", FERRYMEN, "2pm", 30),
])


def test_only_that_afternoon_comes_back_and_earliest_first():
    assert [booking.begins for booking in DIARY.on("06-14")] == ["2pm", "4pm"]


def test_an_afternoon_with_nothing_on_it_comes_back_bare():
    assert DIARY.on("06-21") == []


def test_the_dates_come_back_in_order_and_once_each():
    assert DIARY.dates() == ["06-07", "06-14"]


def test_two_turns_at_the_same_hour_keep_the_order_taken_down():
    both = Diary([
        Booking("07-05", SILVER, "3pm", 45),
        Booking("07-05", FERRYMEN, "3pm", 45),
    ])

    assert [booking.band.name for booking in both.on("07-05")] == [
        "Silver Prize", "The Ferrymen",
    ]
