# masonsyard

The monumental mason's yard at Nether Combe as it keeps its own work, over the
Node standard library alone. There is nothing to install: no `package.json`, no
`node_modules`.

## The modules

- `stones.ts` — the stones standing in the yard, and how one is asked for.
- `orders.ts` — the order book: what the yard has been asked to cut, in the
  order it was asked for.
- `inscription.ts` — how the words somebody gave are set out for the chisel.
- `account.ts` — what the yard charges, and what a quarter of it comes to.

## The house rules

- The yard holds its stones in the order they were rough-hewn.
- A stone is asked for by the mark chalked on its foot, and a mark is matched
  however it was chalked.
- An order is set down as it was taken and is never altered afterwards, and the
  book holds the orders in the order they came.
- An order struck off is out of the book, and the book is the shorter for it:
  what is left standing in it is what is still to cut.
- Nothing goes on a stone that was not asked for in words: every `&` an
  inscription was given is cut in full as `and`, and every one of them is.
- Where an inscription gives two dates, the head of the stone carries the first
  of them; a second date goes lower down and is no business of the head's.
- Lettering is charged by the hundred letters and figures the words were given
  in, and a part hundred is not charged for at all.
- A line of an account is worked out in pence and kept in pence. Only the foot
  of the account is brought to whole shillings, and the odd pence are dropped
  there and nowhere else.

`review.diff` is the change that brought the lettering and the account in, in
the state the yard's own copy of it is in.

Run the tests with `node --test`.
