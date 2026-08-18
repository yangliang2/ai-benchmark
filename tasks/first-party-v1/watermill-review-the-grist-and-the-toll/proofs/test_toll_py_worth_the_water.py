"""The existence proof of the planted finding ('toll.py', 'worth_the_water').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that the stones are not set going for less than a bushel, and
corn is reckoned in pecks, four of them to a bushel. The change holds the pecks
up against a figure written in bushels without bringing the two to the one
measure, so a quarter of what the rule asks for reads as enough.
"""

from toll import worth_the_water


def test_the_stones_are_not_set_going_for_less_than_a_bushel():
    assert worth_the_water(2) is False
    assert worth_the_water(4) is True
