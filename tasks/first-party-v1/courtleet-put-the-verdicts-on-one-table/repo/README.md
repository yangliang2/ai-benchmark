# courtleet

The manor's court leet, over the Node standard library alone. There is nothing
to install: no `package.json`, no `node_modules`.

- `cases.ts` — a `Case`: whom the presentment is against, and what the jury
  found, read off one line of the roll
- `bylaws.ts` — a `Bylaw` out of the parish book: its name, the words the
  parish wrote for when it is broken, the verdict it carries and the pence
- `court.ts` — the `Court`: it tries each bylaw's words against the case in a
  context of their own, and says what it says

A bylaw's words are the parish's own and not the court's: they are run in a
fresh context with `node:vm`, seeing the jury's findings and nothing else, and
given only so long before the court gives up on them. Words that will not run
at all are words the case does not answer to.

Run the tests with `node --test`.
