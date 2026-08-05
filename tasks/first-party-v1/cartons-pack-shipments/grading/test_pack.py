"""How `pack` is graded: by the rules the despatch team gave, not by one
packing.

The strategy is the decision the prompt deliberately leaves open, so nothing
here compares the result against a particular arrangement of items — several
arrangements satisfy the rules for the same shipment and every one of them is
a correct answer. What is checked is that the rules hold, including the one
that costs money: no two cartons that could have travelled as one.

The weighing is done here rather than through the module's own helper: what is
being graded is the packing, and a solution that also changed what a carton
weighs must not be able to move the target.
"""

from itertools import combinations

import pytest
from cartons import Item, pack

CAPACITY = 1000

SHIPMENTS = {
    # Heaviest first: whatever is packed in arrival order leaves the last
    # light item in a carton of its own, next to a carton it would have fitted.
    "descending": [Item("a", 600), Item("b", 500), Item("c", 400), Item("d", 300)],
    "unsorted": [Item("a", 300), Item("b", 600), Item("c", 400), Item("d", 500)],
    "one-each": [Item("a", 900), Item("b", 800)],
    "exact-fit": [Item("a", 1000), Item("b", 250), Item("c", 750)],
    "single": [Item("a", 120)],
    "many-small": [Item(f"s{number}", 150) for number in range(9)],
}

NAMES = sorted(SHIPMENTS)


def weighed(carton):
    """What the items in a carton weigh together, in grams."""
    return sum(item.weight for item in carton)


def packed(name):
    """The cartons `pack` produces for one shipment, as plain lists.

    The shipment is handed over as a copy of its own, so that a solution
    working through the sequence it was given is graded on what it packed
    rather than on what it had left over.
    """
    return [list(carton) for carton in pack(list(SHIPMENTS[name]), CAPACITY)]


@pytest.mark.parametrize("name", NAMES)
def test_every_item_is_packed_exactly_once(name):
    shipped = [item for carton in packed(name) for item in carton]

    assert sorted(shipped) == sorted(SHIPMENTS[name])


@pytest.mark.parametrize("name", NAMES)
def test_no_carton_is_over_the_capacity(name):
    assert all(weighed(carton) <= CAPACITY for carton in packed(name))


@pytest.mark.parametrize("name", NAMES)
def test_no_two_cartons_could_have_travelled_as_one(name):
    """The billed rule. It is also what rules out an empty carton, which
    weighs nothing and so could always have travelled with another."""
    for one, another in combinations(packed(name), 2):
        assert weighed(one) + weighed(another) > CAPACITY


def test_an_item_heavier_than_the_capacity_is_refused():
    with pytest.raises(ValueError):
        pack([Item("a", 300), Item("b", 1001)], CAPACITY)


def test_nothing_to_pack_gives_no_cartons():
    assert list(pack([], CAPACITY)) == []
