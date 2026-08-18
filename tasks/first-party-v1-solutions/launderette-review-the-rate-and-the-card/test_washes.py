from stamps import Card
from washes import Book, Wash


def test_a_wash_is_written_down_in_the_order_it_went_on():
    book = Book()
    card = Card("ada")

    book.take(Wash("ada", "small", 11), card)
    book.take(Wash("ada", "large", 12), card)

    assert [wash.size for wash in book.washes] == ["small", "large"]
    assert card.stamps == 2


def test_the_day_comes_to_what_went_on_it():
    book = Book()
    book.take(Wash("ada", "small", 11), Card("ada"))
    book.take(Wash("bob", "large", 12, soap=True), Card("bob"))

    assert book.takings() == 260 + 420 + 40
