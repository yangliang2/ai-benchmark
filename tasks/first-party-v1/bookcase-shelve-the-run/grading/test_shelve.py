"""How `shelve` is graded: by what a shelving has to be, not by one shelving.

Which stretches of the run share a shelf is the decision the prompt
deliberately leaves open — several layouts satisfy the rules for the same run
and the same width, and every one of them is a correct answer — so what is
checked is that the books all stand where they were put in the order they were
given, that no shelf is over its width, that a stretch of one subject was
never broken across two shelves, and that no shelf but the last was left under
half full while the stretch after it would have fitted.

Every yardstick here is a literal written out beside the run it belongs to,
rather than read back through `runs` or `span`. A layout that came with a
rewritten notion of where one subject gives way to the next would otherwise be
graded against its own reading of the run.
"""

from typing import NamedTuple

import pytest
from bookcase import Book, shelve


class Case(NamedTuple):
    """One run, the shelf width it is laid out at, and the stretches it
    breaks into — titles and millimetres, written out by hand."""

    books: list
    width: int
    stretches: list
    widths: list


CASES = {
    # Three stretches, and room on one shelf for the first two of them.
    "simple": Case(
        books=[
            Book("Tides", "sea", 30),
            Book("Charts", "sea", 20),
            Book("Knots", "sea", 15),
            Book("Bread", "food", 25),
            Book("Sea Air", "health", 40),
        ],
        width=100,
        stretches=[["Tides", "Charts", "Knots"], ["Bread"], ["Sea Air"]],
        widths=[65, 25, 40],
    ),
    # The second stretch does not fit beside the first, so a layout that fills
    # by the book rather than by the stretch breaks the woodwork in two.
    "straddle": Case(
        books=[
            Book("Etching", "art", 40),
            Book("Joints", "wood", 30),
            Book("Lathes", "wood", 50),
        ],
        width=100,
        stretches=[["Etching"], ["Joints", "Lathes"]],
        widths=[40, 80],
    ),
    # One subject, one shelf, and room to spare on the only shelf there is.
    "whole": Case(
        books=[Book("Reefs", "sea", 35), Book("Tides", "sea", 30)],
        width=100,
        stretches=[["Reefs", "Tides"]],
        widths=[65],
    ),
    # A subject that comes round again: two stretches, not one, so the two
    # halves of the sea may sit on different shelves.
    "again": Case(
        books=[
            Book("Tides", "sea", 55),
            Book("Bread", "food", 30),
            Book("Charts", "sea", 45),
        ],
        width=100,
        stretches=[["Tides"], ["Bread"], ["Charts"]],
        widths=[55, 30, 45],
    ),
    # Narrow books, one to a subject, none of which fills half a shelf alone.
    "singles": Case(
        books=[
            Book("Moss", "plants", 20),
            Book("Ferns", "fungi", 20),
            Book("Lichen", "rocks", 20),
            Book("Slate", "roofs", 20),
        ],
        width=100,
        stretches=[["Moss"], ["Ferns"], ["Lichen"], ["Slate"]],
        widths=[20, 20, 20, 20],
    ),
    # A stretch that fills a shelf exactly, and one that fills the next.
    "exact": Case(
        books=[
            Book("Gneiss", "rock", 60),
            Book("Basalt", "rock", 40),
            Book("Cirrus", "sky", 100),
        ],
        width=100,
        stretches=[["Gneiss", "Basalt"], ["Cirrus"]],
        widths=[100, 100],
    ),
}

NAMES = sorted(CASES)

# Neither book is wider than a shelf on its own; together they are one stretch
# that no shelf can hold.
TOO_WIDE = [
    Book("Etching", "art", 40),
    Book("Foundry", "metal", 70),
    Book("Anvils", "metal", 60),
]


def given(name):
    """One run, handed over as a list of its own, so that a solution which
    sorts or consumes what it was given fails the one rule about that and not
    the ones about something else."""
    return list(CASES[name].books)


def laid_out(name):
    """The run laid out on shelves, as lists of titles and their widths."""
    shelves = [list(shelf) for shelf in shelve(given(name), CASES[name].width)]
    return (
        [[book.title for book in shelf] for shelf in shelves],
        [sum(book.width for book in shelf) for shelf in shelves],
    )


@pytest.mark.parametrize("name", NAMES)
def test_every_book_stands_on_one_shelf_in_the_order_it_was_given(name):
    shelved, _ = laid_out(name)

    assert [title for shelf in shelved for title in shelf] == [
        title for stretch in CASES[name].stretches for title in stretch
    ]


@pytest.mark.parametrize("name", NAMES)
def test_no_shelf_is_empty_or_over_its_width(name):
    shelved, taken = laid_out(name)

    assert shelved
    for shelf, room in zip(shelved, taken):
        assert shelf
        assert room <= CASES[name].width


@pytest.mark.parametrize("name", NAMES)
def test_a_stretch_of_one_subject_is_never_split_across_two_shelves(name):
    """The rule the run's own shape imposes, and the one a layout that fills
    by the book rather than by the stretch walks into."""
    shelved, _ = laid_out(name)

    standing = {
        title: number for number, shelf in enumerate(shelved) for title in shelf
    }
    for stretch in CASES[name].stretches:
        assert len({standing[title] for title in stretch}) == 1


@pytest.mark.parametrize("name", NAMES)
def test_no_shelf_but_the_last_is_under_half_full_for_nothing(name):
    """The floor the layout has to clear, checked against the stretch that
    would have gone next: a shelf may be left under half full only where the
    stretch after it would not have fitted on it anyway."""
    case = CASES[name]
    shelved, taken = laid_out(name)
    width_of = dict(zip([tuple(s) for s in case.stretches], case.widths))

    for number, room in enumerate(taken[:-1]):
        if room * 2 >= case.width:
            continue
        starts = shelved[number + 1][0]
        [following] = [s for s in case.stretches if s[0] == starts]
        assert room + width_of[tuple(following)] > case.width


@pytest.mark.parametrize("name", NAMES)
def test_the_run_the_caller_passed_in_is_left_alone(name):
    books = given(name)

    shelve(books, CASES[name].width)

    assert books == CASES[name].books


def test_an_empty_run_gives_no_shelves_at_all():
    assert list(shelve([], 100)) == []


def test_a_stretch_wider_than_a_shelf_is_refused():
    with pytest.raises(ValueError):
        shelve(list(TOO_WIDE), 100)
