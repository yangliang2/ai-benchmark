from entries import Book, Entry


def test_an_exhibitor_may_be_entered_in_one_class_as_often_as_they_like():
    book = Book()
    book.take(Entry("ada", "six pods of peas", 1))
    book.take(Entry("ada", "six pods of peas", 2))

    assert [entry.number for entry in book.of("ada")] == [1, 2]


def test_an_exhibitor_with_no_entry_has_nothing_in_the_book():
    book = Book()
    book.take(Entry("ada", "three onions", 1))

    assert book.of("bob") == []


def test_a_class_judged_a_second_time_is_judged_afresh():
    book = Book()
    entry = Entry("ada", "three onions", 1)
    book.take(entry)

    book.judged(entry, "second")
    book.judged(entry, "first")

    assert entry.place == "first"


def test_an_entry_the_judge_did_not_reach_has_no_placing():
    assert Entry("ada", "three onions", 1).place is None
