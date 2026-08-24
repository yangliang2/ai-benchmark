# What the drifting takings are

The board saw a past quarter's takings change between two printings, with
not one spring crossing changed in the book. Whether that is a defect or a
policy turns on two questions this repository can answer exactly: what the
book actually stores, and what the takings figure claims to be. It is worth
walking the mechanism first, because the ruling follows from it.

The book stores two things (ledger.py): a fare table and the crossing
lines. A crossing line carries no money figure — cross and refund record the
day, the class and the note only, and crossings.py says so in as many words:
the line is the crossing, not the money. So every counting of past takings
prices old lines through whatever fare table stands at the moment of
counting: takings_between looks each line's class up in `fares` as it is
today. And the table itself keeps no history: set_fare replaces the one
undated figure a class has, so once the board changes a fare, the figure
that was in force on any earlier day is gone from the book. Fourpence was
the horse fare all spring; after midsummer the book holds only sixpence, and
nothing in it can say fourpence ever stood. The drift the clerk saw is these
two facts multiplied: undated prices applied to unpriced lines.

## Options considered

**Reading 1 — it is the book's policy, working as built.** On this reading
the book is a tally of traffic, deliberately priced at the fares of the day
you ask: one table, one figure a class, every use of the book consistent
with every other. The takings figure is then "what this traffic comes to at
today's fares" — a restatement, the way a valuation restates old stock at
current prices — and the clerk's two printings differ because they asked the
same question on two different days. The code supports this reading's
coherence: quote, cross, refund and takings_between all read the same table
the same way, and nowhere does the book pretend to a memory it lacks.

**Reading 2 — it is a defect.** On this reading the takings figure claims to
be a record: the money that actually crossed the box's lip in the named
span. The report's own vocabulary is money-shaped — takings, counted out of
the box — and a record that changes when a price changes is wrong by the
meaning of the word. The defect is not in takings_between's arithmetic,
which does what it says; it is that the book never captures the fare at the
moment it is taken, so no honest record of money taken can be computed from
what is stored.

## Trade-offs

Accepting Reading 1 costs the board every backward-looking sum it might
believe. The spring quarter can never again be stated as it was taken; audit
against the cash actually in the box becomes impossible after any fare
change; and the refund path stops being explainable at all — a refund is
priced off the fare table as it stands when the refund is given, so after a
fare change the box hands back a different sum than it took for that same
crossing. The clerk who took fourpence at Lady Day hands back sixpence after
midsummer, and the book calls both lines the same crossing turned back. A
policy of restatement can excuse a report; it cannot excuse the box paying
out money it never took. What Reading 1 buys is simplicity kept: one table,
no dates, nothing to change.

Accepting Reading 2 costs the repair it implies — the crossing line must
start carrying the pence taken (or the table must keep dated figures), and
until then the book's past stays unrecoverable, because the superseded fares
were never written anywhere. It also obliges honesty about the one place the
current behaviour is right: the fare table's two uses are not the same
question. quote prices a crossing not yet made, and for that the figure as
it stands is exactly right — a quote should move the day the board moves the
fare. It is restating money already taken that today's figure cannot do. The
defect ruling is a ruling about takings and refunds, not about quote.

## Recommendation

Tell the board it is a defect. The takings report presents itself as money
— it is counted in pence and the refund path treats its figures as sums to
hand out of a real box — and the refund is the proof by the book's own hand
that the behaviour is not a chosen policy: no board chooses to pay back
sixpence for a fourpenny crossing, yet that is what the code does after
midsummer, for the same reason the printings drifted. A deliberate
restatement policy would at least have priced the refund at the fare taken;
this book cannot, because it never wrote that fare down. The honest
statement of the defect is that the box's past sums cannot be recovered from
the book as it stands — the lines are unpriced and the old fares are gone —
so the repair is for the future: record the pence on the crossing line at
the moment it is taken (or date the fare table), and say plainly that
quarters before the change are estimates at current fares, not records.
quote stays as it is; it was never the same question.
