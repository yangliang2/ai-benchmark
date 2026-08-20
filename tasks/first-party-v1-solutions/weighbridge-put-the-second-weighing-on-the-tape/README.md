# weighbridge

The public weighbridge's tape, over the Node standard library alone. There is
nothing to install: no `package.json`, no `node_modules`.

- `weighings.ts` — one `Weighing`: the ticket, the haulier, loaded and empty,
  and what the load came to
- `frames.ts` — the form one weighing takes on the tape: a fixed-width frame of
  bytes, where the figures sit in it, and the kind byte that says what it is
- `tape.ts` — the `Tape` itself: frames end to end, read back as weighings

Every frame is the same width and the first byte says what kind it is, so a
tape can be read straight through by something that has never heard of half of
what is on it: a frame of an unknown kind is passed over rather than read
wrong. A tape is never written over — putting something on one gives back a
new tape.

Run the tests with `node --test`.
