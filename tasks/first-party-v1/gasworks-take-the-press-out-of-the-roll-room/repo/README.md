# gasworks

The gasworks' roll room, over the Node standard library alone. There is nothing
to install: no `package.json`, no `node_modules`.

- `readings.ts` — a `Reading` off one meter, and the sheet a day's readings are
  written on
- `rollroom.ts` — the `RollRoom`: a day's sheet pressed into a roll, put on the
  shelf under the day it was taken, and opened back out again
- `office.ts` — the office over the roll room: what was taken in on a day, and
  what the works made

A day's readings are written out one to a line, pressed, and put away under the
day they were taken. Nothing here keeps a reading twice: the roll on the shelf
is the only copy there is, and everything the office says about a day it says
by opening that day's roll.

Run the tests with `node --test`.
