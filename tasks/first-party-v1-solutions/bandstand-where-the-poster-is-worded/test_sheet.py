from bands import Band
from diary import Booking, Diary
from sheet import QUIET, Column, Sheet

FERRYMEN = Band("The Ferrymen", 8, "Iris Vane")
SILVER = Band("Silver Prize", 24)

SHEET = Sheet(Diary([
    Booking("06-07", FERRYMEN, "3pm", 45),
    Booking("06-14", SILVER, "2pm", 30),
    Booking("06-14", FERRYMEN, "4pm", 45),
    Booking("06-21", SILVER, "3pm", 45),
]))


def test_the_ordinary_length_is_not_remarked_on():
    assert SHEET.wording("06-07") == "3pm The Ferrymen with Iris Vane"


def test_an_unusual_length_is_said_after_the_band():
    assert SHEET.wording("06-14").startswith("2pm Silver Prize (30 minutes)")


def test_two_turns_are_run_together_in_the_order_the_diary_gives():
    assert SHEET.wording("06-14") == (
        "2pm Silver Prize (30 minutes), then 4pm The Ferrymen with Iris Vane"
    )


def test_a_date_with_nothing_against_it_says_so():
    assert SHEET.wording("07-12") == QUIET


def test_the_dates_are_broken_into_columns_of_at_most_the_given_depth():
    columns = SHEET.columns(2)

    assert [column.heading for column in columns] == ["06-07", "06-21"]
    assert [column.depth() for column in columns] == [2, 1]
    assert isinstance(columns[0], Column)
