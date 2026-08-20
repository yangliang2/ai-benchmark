# seedbank

The seed bank's store, over the Node standard library alone. There is nothing
to install: no `package.json`, no `node_modules`.

- `packets.ts` — a `Packet` of seed, and the card one is written on
- `store.ts` — the `Store`: the drawer of cards under one root, what it holds,
  and how a card is read back and written out
- `cli.ts` — the counter the store is worked from: `run` takes the words
  somebody typed and the root of the drawer, and gives back what to print and
  what to exit with

The store holds one card to a packet, named after the packet and filed under
the root it was told. Nothing in here picks a root of its own: whoever builds
a `Store` says where the drawer is.

Run the tests with `node --test`.

Work the counter with `node cli.ts list` or `node cli.ts show leek`. The drawer
is wherever `SEEDBANK` names, and otherwise the directory you are standing in.
