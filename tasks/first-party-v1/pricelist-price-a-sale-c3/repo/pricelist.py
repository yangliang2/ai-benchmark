"""A shop's price list: what things cost, and the rules that cut the price.

A rule says who it speaks to and what it takes off. `sku` names the one
product a rule speaks to, or is None for a rule speaking to the whole shop;
`floor` is the quantity at or above which the rule bites; `percent_off` is
what it takes off.

A sale is priced by one rule and one only — the highest-ranked rule that
speaks to it — and the list price stands when none does. `rank` is how
narrowly a rule is aimed: a rule naming a sku outranks one speaking to the
whole shop, and among rules aimed alike the higher quantity floor outranks
the lower. Rank decides, not the size of the cut and not the order the rules
were written in, so a narrow rule taking a little off beats a broad one
taking a lot.

Nothing here modifies the price list it is given.
"""

from collections import namedtuple

Rule = namedtuple("Rule", "sku floor percent_off")

PriceList = namedtuple("PriceList", "prices rules")


def new_price_list(prices, rules=()):
    """A price list of list prices in whole pence, cut by `rules`."""
    return PriceList(dict(prices), tuple(rules))


def list_price(price_list, sku):
    """What one of `sku` costs before any rule speaks to it."""
    return price_list.prices[sku]


def speaks_to(rule, sku, quantity):
    """Whether `rule` has anything to say about this sale."""
    return (rule.sku is None or rule.sku == sku) and quantity >= rule.floor


def rank(rule):
    """How narrowly `rule` is aimed. Higher outranks lower."""
    return (rule.sku is not None, rule.floor)


def discounted(amount, percent_off):
    """`amount` less `percent_off` of it, in whole pence, rounded down."""
    return amount - amount * percent_off // 100


def describe_rules(price_list):
    """The price list's rules, one line each, highest-ranked first."""
    return [
        f"{rule.sku or 'anything'} from {rule.floor}: {rule.percent_off}% off"
        for rule in sorted(price_list.rules, key=rank, reverse=True)
    ]
