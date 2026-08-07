from bookcase import Book, describe, runs, span, subjects, titles

RUN = [
    Book("Tides", "sea", 30),
    Book("Charts", "sea", 20),
    Book("Knots", "sea", 15),
    Book("Bread", "food", 25),
    Book("Sea Air", "health", 40),
]


def test_a_stretch_of_books_takes_up_what_they_add_up_to():
    assert span(RUN) == 130


def test_no_books_take_up_no_shelf():
    assert span([]) == 0


def test_books_of_one_subject_standing_together_are_one_stretch():
    assert [titles(stretch) for stretch in runs(RUN)] == [
        ["Tides", "Charts", "Knots"],
        ["Bread"],
        ["Sea Air"],
    ]


def test_a_subject_that_comes_round_again_is_a_stretch_of_its_own():
    again = [RUN[0], RUN[3], RUN[1]]

    assert [titles(stretch) for stretch in runs(again)] == [
        ["Tides"],
        ["Bread"],
        ["Charts"],
    ]


def test_an_empty_run_breaks_into_no_stretches():
    assert runs([]) == []


def test_the_titles_of_a_stretch_come_out_in_the_order_they_stand():
    assert titles(RUN[:2]) == ["Tides", "Charts"]


def test_the_subjects_come_out_in_alphabetical_order_and_once_each():
    assert subjects(RUN) == ["food", "health", "sea"]


def test_no_books_cover_no_subjects():
    assert subjects([]) == []


def test_the_description_has_a_line_per_shelf():
    assert describe([RUN[:2], RUN[2:]]) == [
        "Tides, Charts (50mm)",
        "Knots, Bread, Sea Air (80mm)",
    ]
