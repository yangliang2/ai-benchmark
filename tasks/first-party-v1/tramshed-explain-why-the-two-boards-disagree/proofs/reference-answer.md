# Why the two boards disagree

The question is two commands over one checked-in book - `python cli.py
town` and `python cli.py quay` - and the whole of the disagreement is
one sort key against another: the town board orders text, the quay
board orders minutes, and the pair 9:40 / 10:05 is exactly the pair
that tells them apart.

## What happens

Both commands begin the same way. cli.py loads the book with
`shedbook.load`, and each board function in boards.py filters the same
place: both boards are set from the same workings list in the one book
- `town_board` and `quay_board` each read `book["workings"]` and keep
the workings for their own end. There is one list; the boards are two
readings of it.

Then they sort, and this is where they part. The town board sorts its
cars by the chalked time string itself - its key is `w["leaves"]`, the
text as it stands in the book. The quay board sorts its cars by the
time converted into minutes past midnight - its key is
`minutes_past(w["leaves"])`, which splits the text on the colon and
returns `int(hour) * 60 + int(minute)`.

The book's times are "9:40" and "10:05" at each end, and the book keeps
each time exactly as entered, with no zero padding applied anywhere -
`shedbook.enter` checks the shape of a chalked time and appends it
untouched, and nothing later rewrites it. So the quay board compares
580 against 605 and prints car 3's 9:40 first, the clock order. The
town board compares the strings, and comparing the times as text puts
"10:05" before "9:40" because the character "1" sorts before "9" - the
comparison never gets past the first character. Car 12's 10:05 tops the
town board, above car 7's 9:40.

## Why it comes out that way

The load-bearing decisions, one by one:

- `boards.town_board` sorts with `key=lambda w: w["leaves"]`: the
  written time, compared as text, character by character.
- Text comparison decides at the first differing character, and "1" is
  smaller than "9", so "10:05" sorts ahead of "9:40" however the clock
  reads.
- `boards.quay_board` sorts with `key=lambda w: minutes_past(...)`:
  the same chalked text, but worked into a number first, so ten past
  five-to-ten lands after twenty-to-ten as the clock says it should.
- Both functions filter `book["workings"]` - the same list, loaded
  once - so nothing about the data separates the boards; only the two
  keys do.
- `shedbook.enter` stores the time as chalked: it validates the
  hour:minutes shape but pads nothing, so a one-figure hour reaches
  the town board's text comparison exactly as the foreman wrote it.

boards.py's own docstring carries the history that left the shed this
way: the town board is the shed's first board and lists cars "by the
written time, the way the chalkboard reads", while the quay board went
up later and "works each time into minutes before it orders anything".
The code's reason the boards disagree is that only one of them was ever
taught arithmetic.

## Boundaries and edge behavior

The disagreement needs a one-figure hour standing next to a two-figure
one. A time chalked with a leading zero - "09:40" - is stored with it,
compares as text the same way it compares as minutes, and would put the
town board right; a day whose times all share the same number of hour
figures shows no split at all, which is why the boards can agree for
weeks and part on the first morning a 9-something meets a 10-something.
Neither board is showing entry order: today's book was entered 9:40
first at each end, and the town board still prints 10:05 on top, which
is the sort at work, not the book's sequence. `minutes_past` trusts the
shape `enter` enforced; a malformed time in a hand-edited book would
raise in the quay board's key and leave the town board indifferent,
since text needs no parsing. The `book` command prints the workings as
they stand, unsorted, and an empty or missing book gives both boards
nothing to print.

What the repository alone cannot settle, named rather than papered
over: which board the shed considers right. The quay board matches the
clock and the town board matches the chalkboard's reading order, and
nothing in the code prefers one - there is no shared sort the two could
be corrected to, only the history in the docstring. Whether the foreman
should chalk padded hours instead is a rule for the shed, not for this
code, which accepts either and keeps what it is given.
