# Who should catch the backwards reading

The board's question is not whether the book should catch a dial that reads
lower than the one before it — the two negative bills settle that — but which
of the two standing mechanisms should own the catch. Before choosing, it is
worth being precise about what each mechanism already does, because the code
as it stands leans further one way than a first look suggests, and because
one fact in intake.py makes the naive version of the catch wrong in either
place.

The first fact: read_meter already refuses a bad line at recording time — a
house the book does not know, a dial below nought, a visit dated out of
order, each raised before the line touches the book — so the recording is
where the book already says no, and a backwards-dial check would join
refusals that already exist there. read_meter even reads the house's last
line already, through last_reading, to enforce the day-order rule; the
backwards check needs exactly that line and would find it already fetched.

The second fact: refit puts a fresh meter on the wall, and its docstring
says outright what that does to the dial — the fresh dial starts at nought,
so the first reading after a refit lawfully stands lower than the last one
before it. The drop is the fitting, not the water. So a lower dial is not
always a mistake, and any catch that treats every lower dial as bad — wherever
it lives — is wrong unless it consults the house's fitting day, which the
book keeps on the house's line and which both mechanisms can read.

## Options considered

**Option 1 — intake owns the catch.** Extend read_meter: after the existing
refusals, compare the offered dial with last_reading's, and treat a lower
dial as bad unless the house's `fitted` day falls after the last reading's
day (the one lawful case the book itself records). The change is a few lines
beside the day-order rule, using the same last_reading lookup, and cli.py
does not change: a refused reading fails the `read` command the way an
out-of-order day already does.

**Option 2 — render owns the catch.** Extend usage_between (or bill): while
folding consecutive dials, treat a negative difference as suspect, exempt
the first reading after the house's recorded `fitted` day, and either refuse
to print the bill or print it flagged. Recording stays as permissive as it
is today; the judgment happens where the two dials are first put side by
side now.

## Trade-offs

Option 1 costs a stricter door. A hard refusal at recording can turn away a
true reading when the book itself is behind — a refit done on the wall but
not yet entered in the book makes the lawful next reading look bad — so
intake's catch is only as good as the clerk's discipline about entering
fittings first, and the works must accept that ordering rule. What it buys
is a book that stays clean: the two negative bills both happened because a
bad line got *into* the book, and usage is computed as the difference
between consecutive dial readings, so a backwards reading admitted to the
book falsifies the figure on each side of it — the quarter it ends and the
quarter it starts — and a catch at recording keeps the bad line out of the
book where a catch at reading-out leaves it standing there. Catch it at the
door and no downstream reader needs to think about it.

Option 2 costs exactly that thinking, forever. A catch at reading-out leaves
the bad line standing in the book where a catch at recording keeps it out:
stand, usage_between, bill and every report anyone adds later must each
re-decide what a negative difference means, or silently trust a book that is
known to admit bad lines. The flag also arrives late — at billing, weeks
after the visit, when the reader who could re-check the dial has moved on —
so what render can do is refuse or annotate a figure, never repair the line.
What it buys is a door that never wrongly refuses: a true-but-lower reading
(the not-yet-entered refit) gets recorded, and the ambiguity is surfaced to
a human at the moment money is at stake.

## Recommendation

Give the duty to intake. The recording is where the book already refuses
what it can see is wrong, the backwards check needs only the last reading
that read_meter already fetches plus the fitting day the book already keeps,
and a line stopped at the door protects every reader of the book at once,
where a catch in render protects one function and leaves the book dirty for
the rest. The one honest cost — a refusal when a refit was done but not yet
entered — is a cost the works can carry procedurally (enter the fitting,
then the reading; the error message can say so), whereas Option 2's cost is
structural and permanent: a book that may hold bad lines, and a judgment
re-made in every reading-out for the life of the works. Render's version
also arrives too late to be acted on cheaply. Catch it where the line comes
in.
