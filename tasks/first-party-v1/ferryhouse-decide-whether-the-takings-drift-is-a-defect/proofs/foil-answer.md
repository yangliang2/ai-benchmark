# What the drifting takings are

The behaviour the clerk noticed is the book working exactly as it was built
to, and the board should be told so. The ferry-house book is a small,
deliberate design: one fare table, one figure a class, and a line per
crossing that records the event and not the money. Everything else follows.

## Options considered

**Reading A — policy.** The book is a tally of traffic priced at the fares
of the day you ask. On this reading the takings command answers the question
"what does this traffic come to at the board's fares?" — the only fares
there are, the ones in force. Reprinting the spring quarter after a rise
*should* give a larger figure, for the same reason a warehouse revalues old
stock at new prices: the traffic is historical, the valuation is current.
Every part of the code speaks this reading with one voice. quote prices off
the table as it stands; cross refuses a class with no figure on the table;
takings_between prices every line off the same table the same way. There is
no second price anywhere, no date on a fare, no amount on a line — not as an
oversight, but because the design needs none of them.

**Reading B — defect.** On this reading the takings figure ought to be the
pence the box took in the span, and the book ought to price each line at
the fare of its own day.

## Trade-offs

Reading B has surface appeal — "takings" sounds like money in a drawer — but
adopting it buys the board almost nothing and costs the book its shape. To
price a line at the fare of its day, the book would need dated fare tables
or amounts on every line: a second record to keep, to migrate, and to keep
consistent with the first, all to make two printings of an old sheet agree.
And the board loses nothing by the current design, because nothing is lost:
the sums actually taken at the box for past crossings can be recovered from
the book as it stands — every crossing line is still there with its day and
class, so whoever wants the spring quarter as it was taken can re-reckon it
from the crossings and the table whenever the need arises. A book that can
always be re-reckoned does not need to carry cached arithmetic on every
line.

Reading A costs only a sentence of explanation to the clerk: the takings
sheet is a valuation at current fares, and two valuations on two sides of a
fare rise will differ. That is not a fault to apologise for; it is what
"current fares" means. In exchange the book stays what it is — one table,
one kind of line, every function reading the same two structures with no
special cases.

## Recommendation

Give the board Reading A: the drift is policy, the book working as built.
The design's consistency is the evidence — a defect is a place where the
code betrays its own intention, and this code has one intention visible in
every function: the fare table as it stands is the price of everything,
always. The clerk's surprise is a documentation gap, not a bookkeeping one.
Print on the takings sheet that figures are stated at current fares, teach
the clerk that a pre-rise printing is superseded by a post-rise one, and
leave the code alone. Simplicity that can answer every question it is asked
— today's quote, today's valuation of any span of traffic — should not be
traded away to make yesterday's piece of paper agree with today's.
