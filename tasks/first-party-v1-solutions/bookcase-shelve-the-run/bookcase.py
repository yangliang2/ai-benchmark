"""A run of books, and the shelves they have to go on."""

from collections import namedtuple

# One book: its title, the subject it is filed under, and how much shelf it
# takes up, in millimetres.
Book = namedtuple("Book", "title subject width")


def span(books):
    """How much shelf a stretch of books takes up."""
    return sum(book.width for book in books)


def runs(books):
    """The run broken into stretches of one subject: books of the same subject
    standing next to each other are one stretch, in the order they stand."""
    stretches = []
    for book in books:
        if stretches and stretches[-1][-1].subject == book.subject:
            stretches[-1].append(book)
        else:
            stretches.append([book])
    return stretches


def titles(books):
    """The titles of a stretch of books, in the order they stand in."""
    return [book.title for book in books]


def subjects(books):
    """The subjects the run covers, in alphabetical order and once each."""
    return sorted({book.subject for book in books})


def describe(shelves):
    """One line per shelf, saying what is on it and how much room it takes."""
    return [f"{', '.join(titles(shelf))} ({span(shelf)}mm)" for shelf in shelves]


def shelve(books, width, divider):
    """The run laid out on shelves `width` millimetres wide, a divider
    `divider` wide standing wherever two stretches share one.

    The policy chosen: fill each shelf as far as it goes — a stretch joins the
    shelf being filled where it and the divider before it both still fit.
    """
    shelves = []
    for stretch in runs(books):
        if span(stretch) > width:
            raise ValueError(
                f"the {stretch[0].subject} books take up {span(stretch)}mm, "
                f"which no {width}mm shelf holds"
            )
        shelf = shelves[-1] if shelves else []
        if shelf and span(shelf) + len(runs(shelf)) * divider + span(stretch) <= width:
            shelf.extend(stretch)
        else:
            shelves.append(list(stretch))
    return shelves
