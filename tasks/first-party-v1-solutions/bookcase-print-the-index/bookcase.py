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


def index(books):
    """The printed index: one (subject, titles, width) triple per subject.

    Walked down the run in the order the books stand, so that a subject's
    titles come out in that order and the first copy of a repeated title is
    the one listed — and sorted at the end, because the index is printed in
    alphabetical order of subject rather than in the order of the run.
    """
    listed = {}
    for book in books:
        if not book.subject:
            raise ValueError(f"{book.title} is filed under no subject at all")
        under = listed.setdefault(book.subject, [])
        if book.title not in titles(under):
            under.append(book)
    return [
        (subject, titles(under), span(under))
        for subject, under in sorted(listed.items())
    ]
