"""Getting a shipment of items into cartons for despatch."""

from collections import namedtuple

# One thing to ship: its stock code, and what it weighs in grams.
Item = namedtuple("Item", "sku weight")


def total_weight(carton):
    """What the items in `carton` weigh together, in grams."""
    return sum(item.weight for item in carton)


def fits(carton, item, capacity):
    """Whether `item` can join `carton` without taking it over `capacity`."""
    return total_weight(carton) + item.weight <= capacity


def manifest(cartons):
    """One line per carton: its number, how much is in it, what it weighs."""
    return [
        f"carton {number}: {len(carton)} item(s), {total_weight(carton)}g"
        for number, carton in enumerate(cartons, start=1)
    ]
