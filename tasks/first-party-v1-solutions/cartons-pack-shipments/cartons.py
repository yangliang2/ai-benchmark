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


def pack(items, capacity):
    """The cartons `items` should be despatched in, none over `capacity`.

    Every item goes into the first carton it still fits, and a new carton is
    only opened when no open one has room. That is what keeps two cartons
    from having been one: a carton is only opened for an item every earlier
    carton was already too full to take.
    """
    cartons = []
    for item in items:
        if item.weight > capacity:
            raise ValueError(
                f"{item.sku} weighs {item.weight}g, more than a carton holds"
            )
        for carton in cartons:
            if fits(carton, item, capacity):
                carton.append(item)
                break
        else:
            cartons.append([item])
    return cartons
