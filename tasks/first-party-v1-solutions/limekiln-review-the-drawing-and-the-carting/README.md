# limekiln

The lime kilns at Sheepwash Hill as they keep their own work, over the Node
standard library alone. There is nothing to install: no `package.json`, no
`node_modules`.

## The modules

- `kilns.ts` — the kilns in the bank at the quarry face, and how one is asked
  for.
- `dockets.ts` — the dockets the burners hand in: what was drawn out of a
  kiln, in the order they were handed in.
- `carting.ts` — the loads the carts take away, and the day sheet.
- `spells.ts` — the spells the burners worked the kiln in.

## The house rules

- The bank holds its kilns in the order they were built.
- A kiln is asked for by the mark cut on the plate at its mouth, and a mark is
  matched however it was cut.
- A docket is set down as it was handed in and is never altered afterwards,
  and the book holds the dockets in the order they came.
- A docket says what was drawn as a plain figure of bushels and nothing else.
  Anything else written in that place is no figure at all, and the docket is
  set aside.
- What the day drew is what the dockets carrying a figure come to; a docket
  set aside is drawn by nobody and adds nothing to the day.
- A load is set down on the day sheet as it was loaded, and the sheet names
  every cart that carried away in the order it first loaded.
- The sheet says what a cart carried away; a cart that never loaded carried
  none.
- The burners work the kiln in spells, a spell being the run of dockets one
  burner drew before the next took the kiln over, and the last spell of the
  day is a spell like any other.

`review.diff` is the change that brought the carting and the spells in, in the
state the kiln's own copy of it is in.

Run the tests with `node --test`.
