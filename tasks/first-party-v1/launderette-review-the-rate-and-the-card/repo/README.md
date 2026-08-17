# The launderette

What runs behind the counter of a community launderette: the drums on the
floor, when the doors are open, what a wash costs, and what each person owes
at the end of the day.

## The modules

- `machines.py` — the drums, and what each of them takes.
- `openings.py` — when the doors are open, and when the last load may go on.
- `tariff.py` — what one wash comes to.
- `stamps.py` — the card by the door.
- `washes.py` — the day's book.

## The house rules

- A wash is priced by the size of the drum it goes in, with forty pence on top
  when soap is asked for.
- A wash started from eight at night onwards is sixty pence off. Eight
  o'clock itself is already the cheaper hour: somebody who puts a load on as
  the clock goes round pays the lower price.
- Every ten stamps earn one free wash, and the card is cleared each time it
  does. Somebody who keeps coming earns another free wash on every tenth
  wash, not only on the first ten.
- A free wash comes off the dearest of that person's loads, so that what it
  is worth is the most it can be.

`review.diff` is the change that brought the late rate and the card in, in
the state the shop's own copy of it is in.
