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
