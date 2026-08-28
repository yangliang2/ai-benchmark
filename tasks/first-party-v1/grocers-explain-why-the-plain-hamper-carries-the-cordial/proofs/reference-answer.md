# Why the plain hamper carries the cordial

The question is one run of `python cli.py make-up` over the checked-in
order book, and the short answer is that Mrs Beech's hamper and
Col. Ashton's hamper are packed to one and the same list: the cordial
went into that list once, and both dockets read it back.

## What happens

cli.py loads orders.json and walks the book twice. The first walk makes
up the hampers: for each order it calls `hampers.make_up(customer,
wants)`, then applies any extras with `hampers.add_extra`. Mrs Beech's
order carries no `wants`, so `make_up` takes the standard branch, where
a standard hamper's contents is the standard list object itself rather
than a copy of it - `contents = STANDARD`, no `list(...)`, no slice, no
copy. Col. Ashton's order takes the same branch, so his hamper's
contents is that same object again. Then his extra is applied: adding
an extra appends it into the hamper's contents list in place -
`add_extra` is one `hamper["contents"].append(item)`. That append lands
in `STANDARD`, the list Mrs Beech's hamper also holds.

Dr Vane's order carries `wants`, and a bespoke hamper is packed into a
fresh list built from its order's own wants - the bespoke branch is
`contents = list(wants)`, a new list, touched by nobody else.

The second walk writes the dockets. The dockets are written only after
every order in the book has been made up - cli.py finishes the whole
making-up loop before the printing loop starts - so by the time
Mrs Beech's docket is read off her hamper, the cordial is already in
the shared list. `docket.docket` prints the contents as they stand and
counts them with `len`, so her docket names the four standard items,
the bottle of cordial, and "5 item(s)". Col. Ashton's docket is
identical apart from the name. Dr Vane's reads his own two items.

## Why it comes out that way

The load-bearing decisions, one by one:

- `hampers.make_up` assigns `contents = STANDARD` on the standard
  branch: the hamper does not get a copy of the standard list, it gets
  the module-level list itself.
- Because every standard order goes through that same assignment,
  every standard hamper made up in the run holds the very same
  contents list - Mrs Beech's and Col. Ashton's `contents` are one
  object, not two equal ones.
- `hampers.add_extra` mutates: it appends into the hamper's contents
  list in place rather than building anything new, so the cordial
  lands in the one shared list.
- The extra was applied to exactly the hamper the book named -
  Col. Ashton's - and no lookup went astray; it shows in Mrs Beech's
  docket only because the two hampers share their list.
- cli.py's two-loop shape matters: dockets are written after the whole
  book is made up, so a mutation made while packing a later order is
  visible in an earlier order's docket.
- The bespoke branch's `list(wants)` is why Dr Vane's docket is
  untouched: his contents is a fresh list, not the shared one.

## Boundaries and edge behavior

The sharing is per run. `STANDARD` is rebuilt when hampers.py is
imported, so the mutation does not outlive the process: run `make-up`
again tomorrow on a book without the extra and the plain hamper is
plain again. Nothing writes the mutated list back to disk - orders.json
is only ever read.

Any extra on any standard order lands in every standard hamper of the
run, however many there are and wherever they sit in the book - order
position does not protect Mrs Beech, because the dockets are read after
everything is packed. An extra on a bespoke order, by contrast, appends
into that order's own fresh list and shows on that docket alone. A book
with a single standard order shows nothing odd, since there is no
second hamper to witness the shared list. The `book` command never
makes anything up, so it always reports the orders as written.

What the repository alone cannot settle, named rather than papered
over: the code never says whether packing every standard hamper to the
one list is a deliberate economy or an oversight - the docstring says
the standard hamper "is the same hamper for everybody", and whether
that sentence means the same contents or the same list object is
exactly the ambiguity the code resolves the sharp way. Nothing here
prices the hampers or checks stock; what the shop does about the extra
bottle it never charged for is outside what this code decides.
