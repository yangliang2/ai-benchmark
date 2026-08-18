"""The existence proof of the planted finding ('keepers.py', 'Roll.hives_kept').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that a hive kept between two members is still the one hive.
The change adds up what each member keeps, so the hive two of them keep between
them is counted once for each name against it and the club is credited with a
hive that does not stand in the yard.
"""

from keepers import Keeper, Roll


def test_a_hive_kept_between_two_members_is_counted_once():
    roll = Roll()
    roll.join(Keeper("ann", ["WB2", "WB5"]))
    roll.join(Keeper("bea", ["WB2"]))

    assert roll.hives_kept() == 2
