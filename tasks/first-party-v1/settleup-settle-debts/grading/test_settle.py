"""How `settle` is graded: by what the payments have to achieve, not by one
set of payments.

Which transfers to ask for is the decision the prompt deliberately leaves
open — several sets clear the same books within the budget, and every one of
them is a correct answer — so the balances are replayed through whatever comes
back and checked to land on zero, the payments are checked to be ones real
people could be asked to make, and the count is checked against the budget the
prompt states.

The replay is done here rather than through the module's own helpers: what is
being graded is the answer, and a solution that also changed how balances are
kept must not be able to move the target.
"""

import pytest
from settleup import settle

BOOKS = {
    "pair": {"ana": 500, "ben": -500},
    "two-and-two": {"ana": 700, "ben": 300, "cal": -400, "dee": -600},
    "with-the-square": {"ana": 250, "ben": -250, "cal": 0},
    # The person already square comes first by name: a scheme that chooses
    # whom to route everything through before dropping the people already
    # settled chooses them, and asks for payments they have no part in.
    "square-first": {"ana": 0, "ben": 500, "cal": -500},
    "one-creditor": {"ana": 999, "ben": -333, "cal": -333, "dee": -333},
    "chain": {"ana": 120, "ben": -450, "cal": 800, "dee": -470},
    "all-square": {"ana": 0, "ben": 0},
    "nobody": {},
}

NAMES = sorted(BOOKS)


def replayed(net, transfers):
    """The balances left once every transfer has been made."""
    after = dict(net)
    for transfer in transfers:
        after[transfer.sender] = after.get(transfer.sender, 0) + transfer.amount
        after[transfer.recipient] = (
            after.get(transfer.recipient, 0) - transfer.amount
        )
    return after


def owing(net):
    """The people with something left to settle."""
    return {name for name, amount in net.items() if amount != 0}


@pytest.mark.parametrize("name", NAMES)
def test_the_transfers_leave_everybody_square(name):
    net = BOOKS[name]

    after = replayed(net, settle(net))

    assert all(amount == 0 for amount in after.values())


@pytest.mark.parametrize("name", NAMES)
def test_every_transfer_is_one_a_person_could_be_asked_to_make(name):
    for transfer in settle(BOOKS[name]):
        assert transfer.amount > 0
        assert transfer.sender != transfer.recipient
        assert {transfer.sender, transfer.recipient} <= set(BOOKS[name])


@pytest.mark.parametrize("name", NAMES)
def test_nobody_already_square_is_dragged_in(name):
    settled = owing(BOOKS[name])

    for transfer in settle(BOOKS[name]):
        assert transfer.sender in settled
        assert transfer.recipient in settled


@pytest.mark.parametrize("name", NAMES)
def test_no_more_payments_are_asked_for_than_the_budget_allows(name):
    budget = max(len(owing(BOOKS[name])) - 1, 0)

    assert len(list(settle(BOOKS[name]))) <= budget


@pytest.mark.parametrize("name", NAMES)
def test_the_books_the_caller_passed_in_are_left_alone(name):
    net = dict(BOOKS[name])

    settle(net)

    assert net == BOOKS[name]


def test_books_that_do_not_add_up_to_zero_are_refused():
    with pytest.raises(ValueError):
        settle({"ana": 500, "ben": -400})


def test_nothing_to_settle_gives_no_transfers():
    assert list(settle({})) == []
