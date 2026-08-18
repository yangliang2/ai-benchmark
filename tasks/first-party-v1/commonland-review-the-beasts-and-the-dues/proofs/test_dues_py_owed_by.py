"""The existence proof of the planted finding ('dues.py', 'owed_by').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a beast takes up of a stint what the common says its
kind takes up, and that a kind the common has never priced is refused rather
than passed over as nothing. The change catches the refusal and steps over the
beast, so a goat on the common is billed at nothing and the register that
should not have held it is never questioned.
"""

from dues import owed_by
from graziers import Beast


def test_a_beast_of_a_kind_the_common_never_priced_is_refused():
    refused = False
    try:
        owed_by([Beast("ada", "goat", "AB")])
    except KeyError:
        refused = True

    assert refused, "a goat has never been priced on this common"
