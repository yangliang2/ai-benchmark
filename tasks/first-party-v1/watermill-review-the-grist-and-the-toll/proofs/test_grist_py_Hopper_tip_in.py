"""The existence proof of the planted finding ('grist.py', 'Hopper.tip_in').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that a lot which would take the hopper over what it holds is
turned away and the hopper is left as it stood. The change tips the lot in and
asks afterwards, so the lot it turns away is in the hopper all the same and the
pecks over stay against it.
"""

from grist import Hopper, Lot


def test_a_lot_that_is_turned_away_leaves_the_hopper_as_it_stood():
    hopper = Hopper(12)

    assert hopper.tip_in(Lot("hale", "hale", "wheat", 8, True, True)) is True
    assert hopper.tip_in(Lot("dray", "dray", "barley", 6, True, True)) is False

    assert hopper.pecks == 8
    assert [lot.corn for lot in hopper.lots] == ["wheat"]
