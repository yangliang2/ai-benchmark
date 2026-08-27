# Breaking the hardening of the steep-house log into workable pieces

Before the pieces, the shape of the problem, because the code sets it. The
ruling has two halves — a bad line never stops a reckoning, and no working
ever leaves the file holding less — and the repository's own boundaries
decide how each half divides. The log is one JSON object per line, appended
a line at a time (`log.append` writes its one line and is done), so damage
comes by the line rather than by the file: a torn write or a stray hand
spoils single lines, and setting a bad line aside while the rest are
reckoned is possible exactly because of that format. Reading happens in two
places, not one — `log.read`, which `reckon.py` depends on, and
`monthend.py`, which goes to the file itself — and whole-file writing
happens in one, `log.rewrite`. The pieces below are cut at those seams.

## Pieces

**Piece 1 — the tolerant read, at the one gate.** `reckon.py`'s readers all
take the log through `log.read` — `day` and `standing` both iterate over
what it returns, and the file is parsed in that one place. So the
setting-aside behaviour lands once, in `log.read`: a line that fails to
parse is set aside, not raised, and the good lines come back. Landing it at
that seam covers those reckonings at a stroke rather than being built into
each reader separately.

**Piece 2 — the read contract, decided with Piece 1.** *Bad* is wider than
broken JSON: `reckon.day` indexes `line["day"]`, `line["working"]` and
`line["quarters"]` straight out of each line, so a line that parses as
JSON but lacks a field stops a reckoning just as an unparseable one does.
What `log.read` promises its callers about a set-aside line — which fields
a returned line is guaranteed to carry, and how the set-aside ones are
handed back (a count, a second return, a side list) — is a contract decided
once, for every reader, and it is the design half of Piece 1 rather than a
separate landing.

**Piece 3 — the month-end brought through the gate.** `monthend.carry`
opens and parses the log file on its own — it reads the text off disk and
`json.loads` each line itself — rather than going through `log.read`. So
hardening `log.read` alone leaves the carry still stopped by a bad line.
The plan's choice: bring the carry through the one gate, so Piece 1 covers
it. It should be reworked to take its lines from `log.read` first, before
the tolerant behaviour is called done — the alternative, hardening its
private parse as a piece of its own, leaves two gates to keep honest
forever.

**Piece 4 — the safe rewrite.** `log.rewrite` writes the file whole, in
place: it opens the log for writing and puts the kept lines back one by
one. A failure partway through leaves the log holding less than it held —
the second half of the ruling, breached by the write path rather than the
read path. The piece is a safe write — writing aside and swapping the file
in, or keeping a copy before the rewrite begins — and it is a piece of its
own, separate from the reading side and workable independently of it, since
nothing in Pieces 1–3 touches how the file is written.

**Piece 5 — the accounting for what was set aside.** The ruling says set
aside *and accounted for*, not silently dropped. Two consequences in this
code. The set-aside lines need somewhere to live and someone to face: kept
in a side file or held in the log untouched, and reported where the steward
already looks (`cli.py`'s printed output is the one reporting surface the
repository has). And the carry must not bury them: `monthend.carry` rewrites
the log from what it parsed, so a carry run over a log holding a bad line
would drop that line in the rewrite — set-aside lines must survive the
carry, or the carry must refuse until they are dealt with.

## Order and dependencies

Pieces 1 and 2 are one landing — a tolerant read is meaningless until its
contract says what callers get — and they come first, because Pieces 3 and
5 both lean on the set-aside behaviour existing. Piece 3 follows: the carry
is rerouted through the gate Piece 1 hardened, and only then does *a bad
line never stops a reckoning* hold across the whole repository, because the
carry is the one reckoning the gate does not reach today. Piece 4 is
independent of all of them — it changes the write path only — and can be
worked in parallel from the first day. Piece 5 lands last, over the
finished read and carry, since what it accounts for is what they set aside.

## Open questions and risks

**Where a set-aside line goes.** Held in place, moved to a side file, or
copied out with its line number — the repository cannot settle it. The
excise man checks `standing` against the floors, so whether a set-aside
steeping should freeze the carry until resolved is the maltster's call, not
the code's.

**What *accounted for* must show.** The only reporting surface is the
steward's screen. Whether a count at the end of each command suffices, or
the ledger wants a line of its own, is policy.

**The risk under it all:** the carried line `monthend.carry` writes is
itself a line in the log with a shape unlike the others (`carried`, with a
`summed` map). Piece 2's contract must not quarantine it as bad — a
contract drawn too tight would set aside the house's own arithmetic — and
that boundary case is worth deciding on paper before Piece 1 is written.
