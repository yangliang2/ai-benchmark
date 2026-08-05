from settleup import Expense, balances, outstanding


def test_nothing_spent_leaves_nobody_owing():
    assert balances([]) == {}


def test_a_payer_is_owed_what_the_others_were_charged():
    assert balances([Expense("ana", 900, ("ana", "ben", "cal"))]) == {
        "ana": 600,
        "ben": -300,
        "cal": -300,
    }


def test_an_amount_that_does_not_divide_charges_the_earliest_shares_more():
    assert balances([Expense("ana", 1000, ("ben", "cal", "dee"))]) == {
        "ana": 1000,
        "ben": -334,
        "cal": -333,
        "dee": -333,
    }


def test_expenses_accumulate_across_the_trip():
    net = balances([
        Expense("ana", 400, ("ana", "ben")),
        Expense("ben", 400, ("ana", "ben")),
    ])

    assert net == {"ana": 0, "ben": 0}


def test_the_settled_are_left_out_of_what_is_outstanding():
    assert outstanding({"ana": 500, "ben": -500, "cal": 0}) == ["ben", "ana"]
