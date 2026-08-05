"""Splitting money, in whole cents.

An amount is a whole number of cents. Splitting one never creates a cent and
never loses one: the shares a split hands back add up to exactly the amount
it was given. Where the amount does not divide cleanly, the shares come out
as close to their exact values as whole cents allow, and where that leaves a
choice between two shares the earlier one takes the extra cent.

Amounts, and the numbers a split is made against, are never negative, and a
split the module cannot make is refused rather than guessed at.
"""


def split_evenly(amount, parts):
    """`amount` split into `parts` shares, as equal as whole cents allow.

    The cents left over after dividing go one each to the earliest shares,
    so no two shares differ by more than a cent and the earlier ones are the
    larger.
    """
    if amount < 0:
        raise ValueError(f"cannot split {amount} cents")
    if parts <= 0:
        raise ValueError(f"cannot split into {parts} shares")
    share, over = divmod(amount, parts)
    return [share + 1 if index < over else share for index in range(parts)]


def as_money(cents):
    """`cents` written out as an amount of money."""
    return f"{cents // 100}.{cents % 100:02d}"
