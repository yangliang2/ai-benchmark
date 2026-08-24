# Answering the auditor from the book the granary already keeps

The pleasant surprise of this repository is that the auditor's question is
already answered — it just has not been asked of the right record yet. The
granary keeps a movement line for every delivery in and every issue out, in
entry order, with the day on every line. A dated, append-only journal of
every sack through the door is precisely the raw material a historical
question needs. What is missing is not data but a function.

## Options considered

**Option A — replay the journal.** The movement lines already in the book
are enough, by themselves, to reconstruct what any bin held at the close of
any past day: take the bin's movements dated on or before the asked day, sum
the ins, subtract the outs, and the running figure at the cut-off is the
answer. Concretely, add `holdings_on(book, name, day)` to `report.py`,
built the same way `movements_between` is built today — one pass over
`book["movements"]`, filtering on the bin and on `line["day"] <= day`, which
works because days are ISO strings and compare as text. No file format
change, no new command, nothing for the clerk to learn.

**Option B — start writing day-end snapshots.** Add a nightly `close`
command to `cli.py` that copies every bin's current count into a dated
`closes` table inside the book, and answer the auditor by lookup.

## Trade-offs

Option B is the heavyweight answer. It grows the book file every single day
whether or not anything moved, it duplicates state the journal already
determines, and — decisively — it only answers for days after the granary
starts running it. Ask about last Lady Day and a snapshot table shrugs: the
history it offers begins the day it was adopted, which for this auditor is
no history at all. It also puts a new obligation on the clerk (the nightly
close), and a forgotten evening leaves a hole in the very record that was
supposed to be authoritative.

Option A costs one small, well-shaped function and nothing else. It answers
for the whole span the book has ever covered, right back to the book's first
line, because the journal was there all along; the auditor's question about
any past day becomes a filter and a sum over lines the granary already
trusts. The only real cost is compute — a fold over the movement list on
every question — and at the scale of a granary's book, a linear pass over a
JSON array is nothing. If the book one day grows past that, the fold's
running totals can be memoised then; nothing about Option A closes that door.

## Recommendation

Take Option A. It is the smallest change in the repository, it is the only
option that answers for the past as well as the future, and it treats the
movement journal as what it is: the granary's single source of truth. The
`bins` counts in the book are best understood as a cache of the journal's
running totals, kept so that `stocktake` is one read — and the right way to
answer a question about any other day is the same way the cache was made:
replay the journal to the day the auditor names. Option B would bolt a
second record onto a book that already contains the answer, and every
duplicated record is a future disagreement. One journal, one fold, any day:
that is the whole repair.
