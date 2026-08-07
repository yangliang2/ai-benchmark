"""How `index` is graded: against the printed indexes the prompt spells out.

Every decision is stated — a title shelved twice under one subject, which is
listed once where it first appears; what that subject's width then comes to,
which is the listing and not the copy passed over; and a book filed under no
subject at all, which is refused — so the expected indexes are written out
here in full. This is the zero-crux control the shelving task is read against.
"""

import pytest
from bookcase import Book, index

RUN = [
    Book("Tides", "sea", 30),
    Book("Bread", "food", 25),
    Book("Tides", "sea", 30),
    Book("Charts", "sea", 20),
    Book("Tides", "food", 15),
]


def test_the_index_is_a_triple_per_subject_in_alphabetical_order():
    assert index(list(RUN)) == [
        ("food", ["Bread", "Tides"], 40),
        ("sea", ["Tides", "Charts"], 50),
    ]


def test_a_subject_in_two_stretches_of_the_run_is_still_one_entry():
    run = [
        Book("Tides", "sea", 30),
        Book("Bread", "food", 25),
        Book("Charts", "sea", 20),
    ]

    assert [entry[0] for entry in index(run)] == ["food", "sea"]
    assert index(run)[1] == ("sea", ["Tides", "Charts"], 50)


def test_a_title_shelved_twice_under_one_subject_is_listed_once():
    run = [Book("Tides", "sea", 30), Book("Tides", "sea", 30)]

    assert index(run) == [("sea", ["Tides"], 30)]


def test_the_copy_passed_over_adds_nothing_to_the_width():
    [(_, _, width)] = index([Book("Tides", "sea", 30), Book("Tides", "sea", 45)])

    assert width == 30


def test_the_same_title_under_two_subjects_is_listed_under_both():
    run = [Book("Tides", "sea", 30), Book("Tides", "food", 15)]

    assert index(run) == [("food", ["Tides"], 15), ("sea", ["Tides"], 30)]


def test_the_titles_come_out_in_the_order_the_books_stand_in():
    run = [
        Book("Knots", "sea", 15),
        Book("Charts", "sea", 20),
        Book("Tides", "sea", 30),
    ]

    assert index(run)[0][1] == ["Knots", "Charts", "Tides"]


def test_an_empty_run_gives_an_empty_index():
    assert index([]) == []


def test_a_book_filed_under_no_subject_at_all_is_refused():
    with pytest.raises(ValueError):
        index([Book("Tides", "sea", 30), Book("Waifs", "", 10)])


def test_the_run_the_caller_passed_in_is_left_alone():
    books = list(RUN)

    index(books)

    assert books == list(RUN)
