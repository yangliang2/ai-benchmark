# The cordial in the plain hamper: a docket gone astray

The pleasant thing about this little repository is how faithfully it
keeps the shape of a real back room: an order book read in the morning,
hampers made up one by one, dockets written when the van is loaded.
The bottle of cordial on Mrs Beech's docket is the sort of thing that
happens in a real back room too, and for much the same reason - two
standard hampers standing side by side, and an extra set down by the
wrong one.

## What happens

cli.py opens the order book and works through it in order. Each order
becomes a hamper: each standard hamper starts from its own copy of the
standard list - tea, sugar, fruit cake, marmalade - and a bespoke
hamper is packed from the list the customer sent. Extras are then dealt
with as the book directs.

This is where the day goes wrong. Mrs Beech's order and Col. Ashton's
order are both standard, so by the time the extras are handled the
bench holds two hampers with identical contents and nothing but the
customer's name to tell them apart. The cordial reached Mrs Beech's
hamper through a mix-up of orders - the extra was applied to the wrong
hamper of the two look-alikes, landing one basket over from where the
book pointed. Her docket then honestly reports what her hamper holds:
the four standard items and the bottle, five items in all.

## Why it comes out that way

The making-up loop keeps no firmer grip on a hamper than its position
on the bench, and two standard hampers are indistinguishable by
contents. An extra is a late addition by design - the shop's whole
notion of an extra is something slipped in after the hamper is packed -
so it is applied in a second pass, when the only thing tying it to its
order is bookkeeping the code does not do carefully enough. The bespoke
hamper is immune to the confusion for the homely reason that it looks
different: Dr Vane's potted ham and walnuts could never be mistaken for
a standard hamper, so his docket comes out clean.

Col. Ashton, it is worth noticing, is the loser here: the book promised
him a cordial and his hamper is the one the extra was meant for. The
docket writer itself is blameless - it prints whatever the hamper
holds, and counts it correctly.

## Boundaries and edge behavior

A book with a single standard order cannot show the fault: with only
one hamper on the bench there is nothing to confuse it with. The more
standard orders a book carries, the more chances the extras pass has to
set a bottle down by the wrong basket. Bespoke orders are safe at any
number, for the reason above. The fault is also confined to the day:
nothing about a morning's mix-up is written back to the book, so
tomorrow's run starts fresh. What the code cannot settle is what the
van man does when a customer queries a docket - the shop's remedy for
a misdelivered bottle lives outside this repository.
