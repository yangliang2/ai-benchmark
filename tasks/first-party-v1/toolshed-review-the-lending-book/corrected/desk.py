"""What the desk prints: the board of what is out, and a member's slip."""


def line(loan):
    """One loan as it goes on a slip."""
    return f"{loan.label} ({loan.day})"


def board(book):
    """A line per member with something out, in name order: the member, and
    the labels of what they have out."""
    shown = []
    for who, loans in sorted(book.by_member().items()):
        shown.append(f"{who}: " + ", ".join(loan.label for loan in loans))
    return shown


def slip(book, who):
    """One member's own slip: their loans, oldest first."""
    loans = sorted(book.loans, key=lambda loan: loan.day)
    return [line(loan) for loan in loans if loan.who == who]
