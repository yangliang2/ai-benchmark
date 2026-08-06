"""Held-out grading for `price_for`.

Every expectation is a literal in pence, worked out from the list prices and
percentages written in each test. Nothing here recomputes an answer through
`rank`, `speaks_to` or `discounted` to decide whether it is right, so an
answer that rewrote one of those cannot talk this suite into accepting it.

The suite falls into two halves on purpose. The near half — sales that at
most one rule speaks to — is what a reader trying their own change would
exercise, and a wrong answer passes all of it. The far half is sales that
several rules speak to at once, which is the whole of what the module means
by a sale being priced by one rule.
"""

from pricelist import (
    Rule,
    describe_rules,
    discounted,
    list_price,
    new_price_list,
    price_for,
    rank,
    speaks_to,
)

PRICES = {"kettle": 2400, "mug": 350}


def shop(*rules):
    return new_price_list(PRICES, rules)


# --- the near half: at most one rule speaks ------------------------------------


def test_with_no_rules_at_all_the_list_price_stands():
    assert price_for(shop(), "mug", 4) == 1400
    assert price_for(shop(), "kettle", 1) == 2400


def test_a_shop_wide_rule_cuts_the_price():
    assert price_for(shop(Rule(None, 1, 25)), "kettle", 1) == 1800


def test_a_rule_naming_the_sku_cuts_the_price():
    assert price_for(shop(Rule("mug", 1, 10)), "mug", 4) == 1260


def test_a_rule_naming_another_sku_says_nothing_about_this_sale():
    assert price_for(shop(Rule("kettle", 1, 25)), "mug", 4) == 1400


def test_a_rule_below_its_quantity_floor_says_nothing():
    assert price_for(shop(Rule("mug", 6, 20)), "mug", 5) == 1750
    assert price_for(shop(Rule("mug", 6, 20)), "mug", 6) == 1680


def test_the_cut_is_rounded_down_to_whole_pence():
    assert price_for(shop(Rule("mug", 1, 10)), "mug", 1) == 315


def test_nothing_bought_costs_nothing():
    assert price_for(shop(Rule(None, 1, 25)), "mug", 0) == 0


def test_the_price_list_is_not_modified():
    rules = (Rule(None, 1, 25), Rule("mug", 6, 10))
    price_list = new_price_list(PRICES, rules)

    price_for(price_list, "mug", 6)

    assert price_list.prices == {"kettle": 2400, "mug": 350}
    assert price_list.rules == rules
    assert PRICES == {"kettle": 2400, "mug": 350}


# --- the far half: more than one rule speaks -----------------------------------


def test_a_rule_naming_the_sku_beats_a_shop_wide_one_that_also_speaks():
    assert price_for(shop(Rule(None, 1, 30), Rule("mug", 1, 10)), "mug", 4) == 1260


def test_a_narrow_rule_taking_little_off_beats_a_broad_one_taking_a_lot():
    assert price_for(shop(Rule("kettle", 1, 5), Rule(None, 1, 25)), "kettle", 1) == 2280


def test_among_rules_aimed_alike_the_higher_floor_decides():
    assert price_for(shop(Rule("mug", 1, 5), Rule("mug", 6, 20)), "mug", 6) == 1680


def test_the_rules_the_winner_outranks_are_not_applied_as_well():
    assert (
        price_for(
            shop(Rule(None, 1, 30), Rule("mug", 1, 10), Rule("mug", 6, 15)),
            "mug",
            10,
        )
        == 2975
    )


def test_the_order_the_rules_were_written_in_does_not_decide():
    written_one_way = shop(Rule(None, 1, 30), Rule("mug", 1, 10))
    written_the_other = shop(Rule("mug", 1, 10), Rule(None, 1, 30))

    assert price_for(written_one_way, "mug", 4) == 1260
    assert price_for(written_the_other, "mug", 4) == 1260


def test_a_sale_the_winner_does_not_speak_to_is_priced_by_whoever_does():
    price_list = shop(Rule(None, 1, 30), Rule("mug", 6, 10))

    assert price_list.rules[1].sku == "mug"
    assert price_for(price_list, "mug", 6) == 1890
    assert price_for(price_list, "mug", 5) == 1225


# --- what was already there goes on working ------------------------------------


def test_the_existing_readers_are_unchanged():
    price_list = shop(Rule(None, 1, 30), Rule("mug", 6, 10))

    assert list_price(price_list, "kettle") == 2400
    assert speaks_to(Rule("mug", 6, 10), "mug", 6)
    assert not speaks_to(Rule("mug", 6, 10), "mug", 5)
    assert rank(Rule("mug", 1, 5)) > rank(Rule(None, 1, 30))
    assert discounted(1000, 10) == 900
    assert describe_rules(price_list) == [
        "mug from 6: 10% off",
        "anything from 1: 30% off",
    ]
