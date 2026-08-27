# Breaking the taking of names out of the book into workable pieces

Before the pieces, the shape of the problem, because the code sets it. Names
enter and leave this repository in four ways, not one. The door (`door.py`)
writes who a dole went to into each entry exactly as handed in — `give`
appends `{"day", "who", "kind", "note"}` with the clerk's own words in
`"who"` — so the book as already written holds names entry by entry, on
disk, and Michaelmas does not erase them. The tally (`tally.py`) reads those
stored strings back and matches on them exactly. The clerk's face (`cli.py`)
takes `who` free on the command line. And the notes are prose. The rule
covers the whole book, so the work is as much a migration of what exists as
a change to what will be written, and the pieces below are cut where the
code cuts.

## Pieces

**Piece 1 — the clerk's naming roll.** Nothing in the repository maps a
person to a number — no module or file holds such a roll, and `book.py`
stores only the entries themselves. The roll is therefore a new piece: a
store of number-to-person kept apart from the book (the trustees' rule says
the clerk's alone, never inside it), with a way to assign the next number
and to look a person up. Every other piece leans on this one, because
converting an entry means looking its name up in that roll.

**Piece 2 — the conversion of the stored entries.** Because the door writes
the name into each entry, every entry already in `book.json` is a name
sitting exactly where the visitors will read. The plan must convert or
close out those stored entries: a one-time pass over `entries` that looks
each `"who"` up in the roll of Piece 1 (adding those not yet numbered) and
writes the number in the name's place. This piece is what makes the rule
true of the book "as it already stands", and it cannot run before Piece 1
exists.

**Piece 3 — the door taught to write numbers.** `cli.py` takes `who` free
on the command line and `door.py` writes it through unchecked into the
entry. From Michaelmas, what reaches the book must be the number and not
the name the clerk was given at the door: either the clerk keys in numbers
(looked up by hand in the roll) or the command line takes a name and
translates it against the roll before `give`/`refuse` write. Either way the
translation is a piece of its own, tied to the switch day.

**Piece 4 — the readers, and why halfway is worse than nothing.**
`tally.history` matches each entry's `"who"` to the asked-for `who` by
exact string, and `tally.often` counts by that same string. So a book half
in names and half in numbers splits one person's record in two: the
trustees reading a history before granting more would see only the numbered
half, and `often` would under-count everyone converted partway. The
conversion of the stored entries (Piece 2) and the switch at the door
(Piece 3) must land together, and the readers themselves then need only
that lookups be made by number — plus, where the clerk wants names on the
screen, a translation through the roll at the very edge of `cli.py`, never
written back.

**Piece 5 — the notes, named as the hard residue.** The `note` field is
free prose stored word for word — `refuse` even requires one — and the
repository's own examples put people's names inside notes ("young
Tunnicliffe fetched it"). No mechanical pass can find every name in prose.
The piece here is a clerk's review of the stored notes, and the honest plan
says so rather than folding it silently into Piece 2.

## Order and dependencies

Piece 1 comes first: the roll must exist before the stored entries can be
converted, because the conversion is a lookup into it, and before the door
can translate, for the same reason. Pieces 2 and 3 land together at the
switch — the exact-string matching in `tally.py` is why: converted history
under an unconverted door, or the reverse, splits every active person's
record in two. Piece 4's edge translation and Piece 5's review of the notes
can follow, but Piece 5 must finish before the book goes to the visitors,
since it is the one piece the conversion pass cannot guarantee.

## Open questions and risks

**Names in the notes.** How the stored notes are to be cleared of names is
not decidable from the repository: prose has no schema, and only the clerk
knows which words are names. Whether the trustees accept a clerk's sworn
review, or want the old notes struck entirely, is theirs to fix.

**Refusals and disputes.** A refusal's note exists to justify the refusal,
and stripped of names it may no longer justify anything ("already helped
this week" — helped whom?). Whether a numbered note still serves the
trustees' purpose is a policy question the code cannot answer.

**The risk under it all:** nothing enforces that the roll stays out of the
book. Piece 1 keeps it apart by construction; discipline at the door and in
the notes is what keeps a name from leaking back in, and a later hand that
writes a name into `who` re-inherits today's book silently, because nothing
in `door.py` would refuse it.
