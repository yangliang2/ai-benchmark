# lockhouse

A lock on the cut, and the night the lockhouse keeps at it, over the Node
standard library alone. There is nothing to install: no `package.json`, no
`node_modules`.

- `water.ts` — a `Boat`, and the `Cut` it comes up: the three things that
  reach the lockhouse, and how often each of them happens
- `book.ts` — the `Book` the night is written up in, a line a boat and in the
  order they went through, and how one boat is written up
- `lock.ts` — the `Lock`, which takes one boat and settles when that boat is
  out at the far end, and the `Tally` of what came up to the gate
- `keeper.ts` — the standing `Orders`, and the `Keeper` that keeps one night

Boats come up the cut all evening and the chamber holds one at a time, so a
boat that comes up while another is in the lock waits its turn and goes
through behind it. Every boat that came up is on the page at the end of the
night, in the order it went through, and the night is not over until the last
of them is out at the far end.

Nothing here waits on a length of time. What is waited on is the promise the
work hands back, which settles when the work has been done.

Run the tests with `node --test`.

Start a night with `node keeper.ts`.
