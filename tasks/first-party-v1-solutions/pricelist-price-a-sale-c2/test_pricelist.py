from pricelist import (
    Rule,
    describe_rules,
    discounted,
    list_price,
    new_price_list,
    rank,
    speaks_to,
)


def test_a_price_list_holds_its_list_prices():
    shop = new_price_list({"kettle": 2400, "mug": 350})

    assert list_price(shop, "kettle") == 2400
    assert list_price(shop, "mug") == 350


def test_a_price_list_holds_its_rules_as_given():
    shop = new_price_list({"mug": 350}, [Rule("mug", 6, 10)])

    assert shop.rules == (Rule("mug", 6, 10),)


def test_a_shop_wide_rule_speaks_to_any_sku():
    assert speaks_to(Rule(None, 1, 5), "kettle", 1)
    assert speaks_to(Rule(None, 1, 5), "mug", 1)


def test_a_rule_naming_a_sku_says_nothing_about_another():
    assert speaks_to(Rule("mug", 1, 10), "mug", 1)
    assert not speaks_to(Rule("mug", 1, 10), "kettle", 1)


def test_a_rule_says_nothing_below_its_quantity_floor():
    assert not speaks_to(Rule("mug", 6, 10), "mug", 5)
    assert speaks_to(Rule("mug", 6, 10), "mug", 6)


def test_a_rule_naming_a_sku_outranks_one_speaking_to_the_whole_shop():
    assert rank(Rule("mug", 1, 5)) > rank(Rule(None, 1, 30))


def test_among_rules_aimed_alike_the_higher_floor_outranks_the_lower():
    assert rank(Rule("mug", 12, 5)) > rank(Rule("mug", 6, 5))
    assert rank(Rule(None, 12, 5)) > rank(Rule(None, 6, 5))


def test_discount_is_taken_in_whole_pence_and_rounded_down():
    assert discounted(1000, 10) == 900
    assert discounted(355, 10) == 320
    assert discounted(1000, 0) == 1000


def test_describe_rules_lists_them_highest_ranked_first():
    shop = new_price_list(
        {"mug": 350},
        [Rule(None, 1, 30), Rule("mug", 6, 10), Rule("mug", 1, 5)],
    )

    assert describe_rules(shop) == [
        "mug from 6: 10% off",
        "mug from 1: 5% off",
        "anything from 1: 30% off",
    ]
