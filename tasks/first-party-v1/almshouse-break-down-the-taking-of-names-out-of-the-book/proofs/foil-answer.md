# A plan for numbering the almshouse book

The pleasant thing about this repository is how little of it touches a
name. The book is one JSON file, the table of doles knows nothing of
people, and everything a person's name passes through is the one command
the clerk types at the door. That is where the change belongs. Writing
numbers at the door from the ruled day on is by itself the whole change:
the book as already written and the reading side need no work of their own,
because a book is only ever what gets written into it, and from Michaelmas
what gets written will be numbers.

## Pieces

**Piece 1 — the clerk's habit.** From Michaelmas the clerk types a number
where a name was typed before. The commands take whatever they are given,
so nothing in the code even needs to change; the change is at the keyboard.

**Piece 2 — the printed card.** A card by the door listing the numbers the
clerk uses most, so the queue moves as fast as it did when names were
shouted down the row.

**Piece 3 — the paperwork.** Update the README's examples so a new clerk
learns the numbered style from the first day, and have the trustees minute
the date the rule took effect.

**Piece 4 — a dry run.** For the week before Michaelmas, keep a second book
alongside the real one, worked entirely in numbers, to prove the day's
routine holds up.

## Order and dependencies

The order is the numbering, and it is loose: only the printed card (Piece
2) truly wants doing before the day itself, so the queue does not stall.
Nothing here blocks anything else, which is this plan's strength — the
pieces can be shared among the trustees and done in an afternoon each.
There is no conversion step anywhere in this plan, and that is deliberate:
the book is an append-only record of its days, the old days were lawful
when written, and a record does not need rewriting to obey a rule that
begins at Michaelmas.

## Open questions and risks

The genuine risks are human rather than technical. The clerk will reach for
a name out of habit for a week or two; the card by the door is the cure.
The visitors may ask why the style of the book changes partway through a
page, and the trustees' minute is the answer to show them. Beyond that, the
repository takes this change in its stride: one habit at the door, changed
on the right morning.
