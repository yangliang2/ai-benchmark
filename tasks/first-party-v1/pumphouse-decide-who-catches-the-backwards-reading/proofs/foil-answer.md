# Who should catch the backwards reading

The right home for this catch is render.py, and the argument is short: a
meter is a counter. It counts water through the pipe, and water does not run
backwards up it. A dial reading lower than the house's previous one is
always a mistake — a misread figure, a slipped digit at the keyboard — and
always exactly one kind of thing, which is what makes the catch so cheap to
own at reading-out, where the dials are already put side by side.

## Options considered

**Option A — render owns the catch.** usage_between already walks a house's
readings in pairs; today it simply subtracts. Teach it that a negative
difference is an error: raise, or print the bill with the offending pair
named, so the clerk sees "1927-06-24 read 1721, 1927-09-29 read 63" and
can go and put the book right. One function changes, in the one place the
comparison already happens.

**Option B — intake owns the catch.** read_meter would compare the offered
dial with the house's last and refuse the lower one at the door, beside its
existing refusals.

## Trade-offs

Option B looks tidy but hardens the door in a way this book has been careful
not to. Everything read_meter refuses today is wrong on the face of the one
line — a house that does not exist, a dial below nought, a day out of order.
A dial comparison is a different kind of rule: it makes the door sit in
judgment over the reader's eyes, and a refusal at the door is a reading lost
— the reader is on a round, the refusal lands at the clerk's desk later, and
the visit's figure may never be recovered. The door should record what the
reader called; recording is testimony, not arithmetic.

Option A costs one honest thing: the error is found at billing rather than
on the reading's day. But that is exactly when it matters — no figure in
this book does any harm until it is read out into a bill — and it is the
cheapest possible check, since the subtraction is already there. Because a
lower dial is always an error and nothing else, render can flag every
negative difference with complete confidence and no further record: there is
no case to look up, nothing else to consult, no second table to keep.

## Recommendation

Give the duty to render. It owns the only computation the defect can hurt,
it already holds both dials in its hand, and the rule it needs is total —
flag every negative difference, every time. Intake should stay the thin,
faithful recorder it is: doors that do arithmetic turn readers away, and a
book is better served by taking every reading it is offered and judging them
all in one place, at the moment the money is counted.
