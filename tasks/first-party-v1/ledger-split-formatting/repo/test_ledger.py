from ledger import Ledger


def test_empty_ledger_renders_a_zero_total():
    assert Ledger().render() == "total: $0.00"


def test_render_lists_entries_then_the_total():
    ledger = Ledger()
    ledger.add("rent", 100000)
    ledger.add("coffee", 450)

    assert ledger.render() == "rent: $1000.00\ncoffee: $4.50\ntotal: $1004.50"


def test_total_sums_entries():
    ledger = Ledger()
    ledger.add("in", 500)
    ledger.add("out", -200)

    assert ledger.total() == 300
