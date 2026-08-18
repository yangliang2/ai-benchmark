"""The existence proof of the planted finding ('points.py', 'tally').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a tally asked for with none handed in starts at
nothing. The change writes the empty tally into the signature, where it is
made once and lives as long as the module does, so the second section a
steward brings is added to the first one's points and the first tally grows
under the hand that already read it.
"""

from entries import Entry
from points import tally
from show import Class


def test_a_tally_asked_for_with_none_handed_in_starts_at_nothing():
    classes = [Class("six pods of peas", "vegetables")]

    vegetables = tally([Entry("ada", "six pods of peas", 1, place="first")], classes)
    flowers = tally([Entry("bob", "six pods of peas", 2, place="second")], classes)

    assert vegetables == {"ada": 4}
    assert flowers == {"bob": 3}
