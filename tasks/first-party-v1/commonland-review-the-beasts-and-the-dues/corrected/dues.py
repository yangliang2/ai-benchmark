"""What the year on the common comes to: what one commoner owes for their own
beasts, the herdsman's wage divided between them all, and the reckoning the
reeve sends out."""

from common import gates_for

PENCE_A_GATE = 30


def owed_by(beasts):
    """What one commoner owes for their own beasts: thirty pence for every gate
    those beasts take up. A beast of a kind the common has never priced is not
    the reeve's to pass over as nothing."""
    gates = 0
    for beast in beasts:
        gates += gates_for(beast.kind)
    return gates * PENCE_A_GATE


def share_out(wage, owed):
    """The herdsman's wage divided between the commoners by what their own dues
    come to. What will not divide evenly falls to the commoner who owes the
    most, so the shares always come to the wage; two level on dues leaves it
    with the one the register reached first."""
    total = sum(owed.values())
    if not total:
        return {}
    shares = {who: wage * pence // total for who, pence in owed.items()}
    most = max(shares, key=lambda who: owed[who])
    shares[most] += wage - sum(shares.values())
    return shares


def reckoning(register, wage):
    """What the reeve sends out, commoner by commoner: what they owe for their
    own beasts, and their share of the herdsman's wage on top of it."""
    owed = {
        grazier.who: owed_by(register.turned_out(grazier.who))
        for grazier in register.graziers
    }
    shares = share_out(wage, owed)
    return {who: pence + shares.get(who, 0) for who, pence in owed.items()}
