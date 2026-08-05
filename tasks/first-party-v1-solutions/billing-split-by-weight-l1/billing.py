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


def split_by_weights(amount, weights):
    """`amount` split into one share per weight, in proportion to them.

    Each share starts at the whole cents its exact value covers, which
    leaves a few cents over. Those go to the shares whose exact values that
    rounding cut the hardest, one each, the earlier share taking the cent
    when two were cut alike. A weight of nothing is cut by nothing, so it
    never reaches into what is left over: there are always fewer cents over
    than there are shares that were cut at all.
    """
    if amount < 0:
        raise ValueError(f"cannot split {amount} cents")
    if any(weight < 0 for weight in weights):
        raise ValueError("cannot split against a negative weight")
    total = sum(weights)
    if total <= 0:
        raise ValueError("cannot split against weights adding up to nothing")

    shares = []
    cut_by = []
    for index, weight in enumerate(weights):
        share, remainder = divmod(amount * weight, total)
        shares.append(share)
        cut_by.append((-remainder, index))
    for _, index in sorted(cut_by)[: amount - sum(shares)]:
        shares[index] += 1
    return shares


def as_money(cents):
    """`cents` written out as an amount of money."""
    return f"{cents // 100}.{cents % 100:02d}"
