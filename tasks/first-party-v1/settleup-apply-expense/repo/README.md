# settleup

Shared-trip bookkeeping, standard library only. Money is whole cents.

- `Expense(payer, amount, shares)` — something somebody paid for.
- `Transfer(sender, recipient, amount)` — one payment between two people.
- `balances(expenses)` — everybody's net balance after a trip.
- `outstanding(net)` — who still has something to settle.

Run the tests with `pytest`.
