# remit

What a customer still owes, invoice by invoice, standard library only.

- `Invoice(reference, raised, amount, paid)` — one invoice: money in whole
  pence, `raised` a whole number of days since the ledger was opened.
- `owing(invoice)` — what is still owed on one invoice.
- `settled(invoice)` — whether it has been paid in full.
- `outstanding(invoices)` — what is still owed across all of them.
- `raised_before(invoices, day)` — the invoices raised before a given day.
- `describe(invoices)` — a printable line per invoice.

Run the tests with `pytest`.
