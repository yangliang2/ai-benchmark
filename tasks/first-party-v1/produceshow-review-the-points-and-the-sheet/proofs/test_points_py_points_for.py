"""The existence proof of the planted finding ('points.py', 'points_for').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a judged entry is worth four points for a first, three
for a second and two for a third, and that a first in a championship class is
worth double. The change asks the table first and returns out of it, so the
championship stands under a rule that has already answered for it and a first
in the championship class is worth the same four as any other.
"""

from entries import Entry
from points import points_for


def test_a_first_in_a_championship_class_is_worth_double():
    entry = Entry("ada", "the heaviest marrow", 12, place="first")

    assert points_for(entry, True) == 8
