# pricelist

Standard-library helpers for a shop's price list: list prices in whole pence,
and the rules that cut them.

- `new_price_list(prices, rules=())` — a price list
- `list_price(price_list, sku)` — what one costs before any rule speaks
- `speaks_to(rule, sku, quantity)` — whether a rule has anything to say
- `rank(rule)` — how narrowly a rule is aimed; higher outranks lower
- `discounted(amount, percent_off)` — the cut, in whole pence, rounded down
- `describe_rules(price_list)` — the rules, highest-ranked first

A sale is priced by one rule: the highest-ranked rule that speaks to it. Rank
is about how narrowly a rule is aimed, not about how much it takes off.

Run the tests with `pytest`.
