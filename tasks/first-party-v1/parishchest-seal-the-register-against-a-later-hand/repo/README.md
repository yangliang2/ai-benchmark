# parishchest

The parish register, and the wax it is sealed with, over the Node standard
library alone. There is nothing to install: no `package.json`, no
`node_modules`.

- `entries.ts` — one `Entry`: the day, what happened, whose hand, and the one
  line an entry reads as
- `seals.ts` — how a seal is taken over a text, in hex of one width, and what
  stands before the first entry of a register
- `register.ts` — the `Register`: entries in the order they were entered,
  counted from one, and never written over

`seals.ts` knows how to seal a text and nothing else. What is sealed onto what
is the register's own business.

Run the tests with `node --test`.
