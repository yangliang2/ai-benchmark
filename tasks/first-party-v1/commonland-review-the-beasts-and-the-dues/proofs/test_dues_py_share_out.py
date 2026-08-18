"""The existence proof of the planted finding ('dues.py', 'share_out').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that what will not divide evenly falls to the commoner who
owes the most, so the shares of the herdsman's wage always come to the wage.
The change divides and stops, so the odd pence are dropped and the herdsman is
paid short of what the commoners were charged.
"""

from dues import share_out


def test_the_shares_of_the_wage_always_come_to_the_wage():
    shares = share_out(100, {"ada": 100, "bob": 200})

    assert sum(shares.values()) == 100
    assert shares == {"ada": 33, "bob": 67}
