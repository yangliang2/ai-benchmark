# Breaking the move to the new money into workable pieces

Before the pieces, the shape of the problem, because the code sets it. Money
lives in four places in this repository, not one. The table (`tariff.py`)
prices each kind in whole pence. The gate (`gate.py`) reckons the charge at
crossing time and writes it into the roll line — `cross` appends
`{"day", "kind", "charge", "note"}` with the charge already computed — so
the roll on disk holds amounts, not just kinds. The till (`till.py`) reads
those stored amounts back: `takings` sums the day's charges as they stand,
and `misrecorded` compares each stored line's charge against the *current*
table's rate for its kind. And the keeper's face (`cli.py`) writes every
amount with its own `pence` helper, as "5d." A change of money therefore
passes through every module, and the pieces below are cut where the code
cuts.

## Pieces

**Piece 1 — a unit marker in the roll file.** A saved roll carries no
version or unit marker anywhere: `roll.fresh` makes `{"lines": []}`, and
`load`/`save` move the file whole with nothing in it that names the money
its charges are in. Add a marker — a top-level field written by `save`,
defaulted by `load` for files that lack it — so that a roll written before
the switch and a roll written after can be told apart by reading them.
Old-pence rolls are the default; the switch flips what `fresh` writes.

**Piece 2 — the cut-over of the stored lines.** Because the gate writes the
reckoned charge into each line, every line already on the roll is an
old-pence amount sitting in the same file the new-pence lines will land in.
The plan must convert, mark or cut over those stored lines: either a one-time
conversion pass over `lines` on the switch day (marker flipped in the same
write), or a fresh roll begun at Lady Day with the old one closed and kept.
I recommend the fresh roll — the old file stays the record of what was
actually taken — but either way this piece exists, and `takings` is the
reason: it sums charges blindly, and a roll with both monies in it sums
pence to pence-that-are-not-pence.

**Piece 3 — the new table.** `tariff.RATES` re-set in new pence, with the
figures the parish fixes (see the open questions: they cannot be computed).
The table's contract — whole integer amounts, unknown kinds refused — stays
as it is.

**Piece 4 — the audit taught which money a line is in.** `misrecorded`
checks `line["charge"] not in (0, tariff.rate(line["kind"]))` — each stored
charge against the current table. The moment the table is re-rated, every
line taken under the old table fails that comparison: the audit would report
the whole history as taken down wrong. It must read the marker of Piece 1
(or run only over new-money rolls) before or together with Piece 3.

**Piece 5 — the keeper's face.** `cli.pence` writes every amount as "5d." —
in `takings`, in `check`, in `rates` — and "d." is the old money's mark. The
formatting switches with the table: new figure, new mark, in the same
landing as Piece 3, so the keeper is never shown the old money's mark on
new-money figures.

## Order and dependencies

Piece 1 comes first, because everything else leans on it: until a roll can
say which money it is in, neither the cut-over (Piece 2) nor the audit
(Piece 4) has anything to read. Piece 2 depends on Piece 1 and must land at
the switch day itself. Pieces 3, 4 and 5 land together, as one change: the
code ties them — `till.misrecorded` reads `tariff` directly, so a new table
with an untaught audit condemns the history (Pieces 3 and 4 cannot ship
apart), and `cli.py` prints the table and the takings the keeper acts on, so
a new table behind an old "d." misleads at the till (Pieces 3 and 5 cannot
ship apart either). The one order that works: marker, then cut-over, then
table + audit + face in a single landing at Lady Day.

## Open questions and risks

**The new figures themselves.** The table's rates do not convert to whole
figures in the new money: at two and two-fifths old pence to the new penny,
the cart's 5d. comes to 2 1/12 new pence, the horse's 2d. to 5/6, the
foot's 1d. to 5/12. Whole-figure rates are a decision, not a conversion —
round the foot crossing up to a halfpenny or down to nothing, and the
parish has cheapened or dearened the toll either way. The repository cannot
settle it; the parish must fix the new figures before Piece 3 can be
written.

**Whether fractions enter the till.** If the parish fixes half-penny rates,
`int` amounts stop sufficing and the smallest unit of account has to be
chosen (half-new-pence as integers would keep every module's arithmetic
whole). Decidable only once the figures are fixed.

**The risk under it all:** nothing enforces that a module reading a roll
checks its marker. Piece 1 makes the money legible; discipline in Pieces 2
and 4 is what makes it honest, and a later reader that ignores the marker
reinherits today's ambiguity silently.
