# billing

Standard-library helpers for splitting money, in whole cents.

- `split_evenly(amount, parts)` — an amount split into equal shares
- `as_money(cents)` — an amount written out

A split never creates or loses a cent, and where the amount does not divide
cleanly the shares land as close to their exact values as whole cents allow,
the earlier share taking the extra cent when that leaves a choice.

Run the tests with `pytest`.
