# The mill

The watermill at Nether Ditchling as the parish grinds at it: which pairs of
stones turn, who brings corn to them, what has been brought in to be ground,
and what the mill takes for grinding it.

## The modules

- `mill.py` — the mill itself: the pairs of stones, the water that drives
  them, and the measures a lot is reckoned in.
- `growers.py` — the round: who brings corn here, and the farms it comes off.
- `grist.py` — the grist book: what has been brought in, and the hopper it
  waits in over the stones.
- `toll.py` — what the mill takes for grinding, and what a book of it comes to.

## The house rules

- The round holds its growers in the order they came on, and puts one on as
  they are given: two of one name is for the miller to sort out and not the
  round's to refuse.
- A pair of stones is asked for by the name it goes by, and a name is matched
  however it was written down.
- Two pairs on the one floor are on the one floor, and it is counted once.
- Corn is reckoned in pecks: four pecks to a bushel, and eight to a sack.
- What will not fill a bushel is not a bushel, and is left out of the reckoning
  in bushels.
- A lot part filling a sack still takes a sack to carry it off: what will not
  fill one is carried in a sack of its own.
- A lot is set down in the book as it was brought in, and the book holds the
  lots in the order they came.
- The book answers for a name with the lots of that grower's own corn and the
  lots that name brought in for a neighbour, both together.
- A lot goes to the stones when it has dried and it has been weighed at the
  door: damp corn will not grind, and what was never weighed cannot be tolled.
- The hopper holds what it holds and no more: a lot that would take it over is
  turned away, and the hopper is left as it stood.
- The mill takes a peck in every sixteen and no part of a peck, off each lot as
  it goes to the stones.
- The stones are not set going for less than a bushel: the water it takes to
  start them is worth more than the toll on a smaller lot.

`review.diff` is the change that brought the grist book and the toll in, in the
state the mill's own copy of it is in.
