# telegraph

One day at a telegraph office, over the Node standard library alone. There is
nothing to install: no `package.json`, no `node_modules`.

- `tape.ts` — the `MARK` that stands between one message and the next, and the
  `Drum` the day's tape comes off, a length at a time
- `messages.ts` — a `Wire`, and the `Cutter` that reads the tape into wires:
  where one message ends and where the next begins
- `charges.ts` — what a message costs, and the `Rate` that prices every one
- `sheet.ts` — the day sheet: the `Repeats` that marks a message sent to the
  same hand as the one before it, the `Totting` that writes the page up and
  foots it, and the `Sheet` itself
- `office.ts` — the run from the drum to the sheet, and one day worked through

The tape comes off the drum a length at a time, and no faster than the far end
of the office will take it, so a long day costs the office no more room than a
short one. A message may end in the middle of a length and a message may run
out of one length into the next: what separates one from another is the mark
and nothing else. The last message of the day has no mark after it, because
nothing was sent after it, and it is a message like any other — read off,
charged, and written up in its place.

Nothing here waits on a length of time. What is waited on is the promise the
day's work hands back, which settles when the work has been done.

Run the tests with `node --test`.

Work one day through with `node office.ts`.
