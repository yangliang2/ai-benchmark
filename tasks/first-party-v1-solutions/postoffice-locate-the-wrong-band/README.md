# postoffice

The counter at the sub-post office, in the standard library alone.

- `parcels.py` — a `Parcel`, and the two readings taken off one: what the
  scale made of it and what the gauge made of it, each as a band
- `card.py` — the card on the wall, and what it says against a band
- `counter.py` — `Window`, a day's parcels as they came over the counter, and
  `Charge`, one of them priced up
- `office.py` — `Office`, which packs the sacks, keeps the notes and makes up
  the book for the day

What a parcel costs to send comes off the card against what the scale made of
it. What the gauge made of it settles which sack it leaves in, and nothing
else: the two readings answer one question each and neither stands in for the
other.

Run the tests with `pytest`.
