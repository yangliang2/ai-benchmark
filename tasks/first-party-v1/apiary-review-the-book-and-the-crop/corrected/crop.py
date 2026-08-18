"""What a summer's crop comes to: how many pounds came off, what they fill, and
what a hive gave on the average."""

from apiary import jars


def taken_in(book, summer):
    """How many pounds came off in this summer, all told."""
    return sum(take.pounds for take in book.takes if take.summer == summer)


def jars_of(book, summer):
    """What the crop of this summer fills, in whole jars."""
    return jars(taken_in(book, summer))


def off_a_hive(book, summer):
    """What a hive gave on the average in this summer: that summer's crop over
    the hives it came off, a hive robbed twice in the one summer counting once,
    in whole pounds with the odd pounds left out."""
    hives = {take.mark for take in book.takes if take.summer == summer}
    if not hives:
        return 0
    return taken_in(book, summer) // len(hives)
