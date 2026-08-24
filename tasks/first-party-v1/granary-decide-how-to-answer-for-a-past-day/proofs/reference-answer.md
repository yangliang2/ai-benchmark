# How the granary should come to answer for a past day

The auditor's question is "what did bin such-and-such hold at the close of
such-and-such a day?", and the book as this repository keeps it cannot answer
that for an arbitrary past day. Before weighing options it is worth being
precise about why, because the reason rules some tempting options out.

The book (`ledger.py`) carries two records: `bins`, the current counts, and
`movements`, a line per delivery in and per issue out. The movement lines
look like a journal, but they are not a complete one, in two places, both in
`book.py`. First, open_bin sets a bin's starting count without writing any
movement line: the sacks a bin was opened with appear only in the bin's own
`sacks` field, so replaying the movements from an empty book does not arrive
at today's counts — every bin comes out short by its opening count. Second,
set_right rewrites a bin's count without writing any movement line: the
annual stocktake sets `sacks` to whatever the counting found, keeps only the
day on the `counted` field, and discards the size of the drift it corrected
— so working backwards from today's counts goes wrong across any correction,
because the subtraction crosses a jump the movements never recorded. The
movement lines record the door; two of the three ways a count changes never
went through the door.

## Options considered

**Option 1 — derive history from the movement lines as they are.** Add a
`holdings_on(book, name, day)` to `report.py` that reconstructs a past count
arithmetically: either forward, by starting from nothing and applying every
movement dated on or before the asked day, or backward, by starting from
today's `sacks` and undoing every movement dated after it. No schema change,
no new writing discipline; days compare as ISO strings already, so the
filtering is one pass over `movements`.

**Option 2 — journal every change of a count, then derive.** Make the
movement record actually complete: have open_bin write an opening line and
have set_right write a correction line carrying the difference between the
counted figure and the figure it replaced, alongside the field updates they
already do. From the day this lands, every change to any bin's `sacks` has a
dated line, and the `holdings_on` of Option 1 becomes correct by
construction — one backward fold from the current count over lines the book
is now guaranteed to have.

**Option 3 — keep day-end counts beside the book.** Snapshot instead of
derive: on every save (or on a nightly `close` command), append each bin's
current count under the day's date to a `closes` record. Answering the
auditor is then a lookup, not a fold.

## Trade-offs

Option 1 costs nothing to adopt and is wrong on this repository's own code.
The forward fold misses every opening; the backward fold is right only for
bins never touched by set_right, and nothing in the book marks which past
stretches are clean. A figure that is silently wrong across corrections is
worse for an audit than no figure.

Options 2 and 3 are both honest, and the choice between them is the real
decision. Deriving from a complete journal (Option 2) keeps one record that
cannot disagree with itself, and answers at any granularity — the close of a
day, or the moment before one issue — but its cost is that every answer is a
fold over the whole movement list, and its correctness depends on every
future count-changing path writing its line: a fourth mutator added to
`book.py` without a movement line would quietly reopen today's hole.
Snapshots (Option 3) make the auditor's exact question a cheap lookup, but
their cost is a second copy of state that can drift from the record that
made it — the same disease `bins` versus `movements` has today, kept on
purpose — and they answer only at the granularity that was snapshotted:
day-end and nothing finer, forever.

Either way, one limit has to be said out loud rather than papered over: past
days from before the change stay unanswerable. The book never recorded what
answering for them would need — the openings and the corrections are gone —
and neither a completed journal nor a snapshot table invents them. The
auditor gets the truth from the adoption day forward, and an honest "the
book cannot say" behind it.

## Recommendation

Take Option 2: journal every change of a count, and derive past holdings
from the completed record. I recommend it over Option 3 because this
repository already leans that way — `movements` is the record the granary
trusts enough to keep line by line, and completing it fixes the root cause
(count changes the journal never sees) rather than adding a second derived
record that inherits it; a snapshot table would still be built over the same
incomplete journal and could still be contradicted by it. Option 2 is also
the smaller change to the code as it stands: two writers in `book.py` each
gain one appended line, `report.py` gains one fold, and `cli.py` does not
change at all. If the fold over a long book ever becomes slow, Option 3's
day-end table can be added later as a cache derived from the journal — the
reverse migration, deriving a journal from snapshots, is impossible. And to
keep the journal complete as the code grows, the rule the two fixed writers
establish — no change to a bin's `sacks` without a movement line — is cheap
to assert in one place at save time, by refusing to save a book whose counts
disagree with a replay of its own lines.
