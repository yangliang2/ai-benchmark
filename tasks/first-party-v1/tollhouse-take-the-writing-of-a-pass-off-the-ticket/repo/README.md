# tollhouse

The tollhouse at the turnpike gate, over the Node standard library alone. There
is nothing to install: no `package.json`, no `node_modules`.

- `tolls.ts` — the table on the tollhouse wall: what each class of traffic is
  charged the axle, and what is added for a laden load
- `tickets.ts` — a `Ticket`: one pass through one gate, what is owed on it, and
  the link a pass is written as
- `gate.ts` — the `Gate` itself: it writes a pass out for the traffic in front
  of it, reads one back when it is handed in, and takes the day's money

A pass is written as a link, under the `toll:` scheme — `toll://westgate/pass`
with the class, the axles and the load in the query — so that a pass can be
handed on, written down, or read back at another gate without anything of the
tollhouse's travelling with it. Reading a link back is `node:url`'s work.

Run the tests with `node --test`.
