/**
 * Held out: what the office says about a bag nobody wrote a weight down for.
 *
 * The agent never sees this file. It asserts what the office *answers* and not
 * how it answers it: where the charge stops being made up is the fix's own
 * business, and a repair anywhere along the way that leaves the bag off the
 * takings and its ticket on the list to go back on the scales passes here.
 *
 * Nothing here names a port. The service is put on port 0 and asked on
 * whatever the machine handed back, so a verdict is never a fact about what
 * was already listening where this happened to be graded.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Charges, Tariff } from "./charges.ts";
import { Desk, serve } from "./desk.ts";
import { Bag, NOT_WEIGHED, Shelf } from "./shelf.ts";

const TARIFF = new Tariff(2, 1);

/** The morning the scales were out: ticket 13 came in and was never weighed. */
function theMorningTheScalesWereOut(): Desk {
  const shelf = new Shelf([
    new Bag(11, 2, 9, "Mrs Dando"),
    new Bag(12, 1, 21),
    new Bag(13, 4, NOT_WEIGHED, "the man off the 8.40"),
  ]);
  return new Desk(new Charges(shelf, TARIFF));
}

function listening(desk: Desk): Promise<{ port: number; shut: () => Promise<void> }> {
  const server = serve(desk, 0);
  return new Promise((ready) => {
    server.on("listening", () => {
      const address = server.address();
      const port = typeof address === "object" && address !== null ? address.port : 0;
      ready({ port, shut: () => new Promise((shut) => server.close(() => shut())) });
    });
  });
}

test("the counter asks nothing for a bag nobody wrote a weight down for", () => {
  const answered = theMorningTheScalesWereOut().answer(13);

  assert.notEqual(answered.status, 200);
  assert.equal(answered.body.owed, undefined);
});

test("that bag goes on the list to be put back on the scales", () => {
  const cashed = theMorningTheScalesWereOut().cashUp();

  assert.deepEqual(cashed.weighAgain, [13]);
});

test("the takings are what the office arrived at and nothing besides", () => {
  const cashed = theMorningTheScalesWereOut().cashUp();

  assert.equal(cashed.takings, 45);
});

test("the bags the scales did reach are answered for exactly as before", () => {
  const desk = theMorningTheScalesWereOut();

  assert.deepEqual(desk.answer(11), {
    status: 200,
    body: { ticket: 11, owed: 22, note: "" },
  });
  assert.equal(desk.answer(12).status, 200);
  assert.deepEqual(desk.book(), [
    "ticket 11: 9",
    "ticket 12: 21",
    "ticket 13: not weighed",
  ]);
});

test("over the counter, the unweighed bag is not asked for money", async () => {
  const { port, shut } = await listening(theMorningTheScalesWereOut());
  try {
    const replied = await fetch(`http://127.0.0.1:${port}/bag/13`);
    const said = await replied.json();

    assert.notEqual(replied.status, 200);
    assert.equal(said.owed, undefined);
  } finally {
    await shut();
  }
});

test("at the end of the day the till and the list say the same thing", async () => {
  const { port, shut } = await listening(theMorningTheScalesWereOut());
  try {
    const replied = await fetch(`http://127.0.0.1:${port}/takings`);

    assert.equal(replied.status, 200);
    assert.deepEqual(await replied.json(), { takings: 45, weighAgain: [13] });
  } finally {
    await shut();
  }
});
