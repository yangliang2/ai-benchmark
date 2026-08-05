"""Working out who owes whom after a shared trip.

Money is whole cents throughout. A balance is what a person is owed: positive
means the group owes them, negative means they owe the group, and a set of
balances always adds up to zero.
"""

from collections import namedtuple

# Something one person paid for, and the people it was for.
Expense = namedtuple("Expense", "payer amount shares")

# One payment: `amount` cents moving from `sender` to `recipient`.
Transfer = namedtuple("Transfer", "sender recipient amount")


def balances(expenses):
    """The net balance of everybody named in `expenses`.

    An expense is charged to its shares in equal whole cents; when the amount
    does not divide evenly, the earliest shares in the order given are the
    ones charged the extra cent.
    """
    net = {}
    for expense in expenses:
        each, extra = divmod(expense.amount, len(expense.shares))
        net[expense.payer] = net.get(expense.payer, 0) + expense.amount
        for position, name in enumerate(expense.shares):
            charge = each + (1 if position < extra else 0)
            net[name] = net.get(name, 0) - charge
    return net


def outstanding(net):
    """The people with something left to settle: those who owe, then those
    who are owed, each group in alphabetical order."""
    return sorted(
        (name for name, amount in net.items() if amount != 0),
        key=lambda name: (net[name] > 0, name),
    )


def applied(net, expense):
    """The balances that result from charging `expense` to `net`."""
    if not expense.shares:
        raise ValueError("an expense nobody shares cannot be charged")
    charged = dict(net)
    each, extra = divmod(expense.amount, len(expense.shares))
    charged[expense.payer] = charged.get(expense.payer, 0) + expense.amount
    for position, name in enumerate(expense.shares):
        charge = each + (1 if position < extra else 0)
        charged[name] = charged.get(name, 0) - charge
    return charged
