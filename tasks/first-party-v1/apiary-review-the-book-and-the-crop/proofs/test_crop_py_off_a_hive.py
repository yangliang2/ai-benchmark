"""The existence proof of the planted finding ('crop.py', 'off_a_hive').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that what a hive gave on the average is the summer's crop over
the hives it came off, a hive robbed twice in the one summer counting once. The
change divides by the lots the crop came off in instead, so a summer in which
one hive was gone through twice reads as a summer with an extra hive in it.
"""

from crop import off_a_hive
from harvest import Book, Take


def test_the_average_is_taken_over_the_hives_the_crop_came_off():
    book = Book()
    book.take_off(Take("WB2", 2026, 30, "ann"))
    book.take_off(Take("WB2", 2026, 20, "ann"))
    book.take_off(Take("WB5", 2026, 10, "bea"))

    assert off_a_hive(book, 2026) == 30
