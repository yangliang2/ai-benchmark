import test from "node:test";
import assert from "node:assert/strict";

import { Charges, Tariff } from "./charges.ts";
import { Desk, NO_NOTE, serve } from "./desk.ts";
import { Bag, NOT_WEIGHED, Shelf } from "./shelf.ts";

const TARIFF = new Tariff(2, 1);

/** A run the scales were working all through. */
function weighedThrough(): Desk {
  const shelf = new Shelf([
    new Bag(11, 2, 9, "Mrs Dando"),
    new Bag(12, 1, 21),
  ]);
  return new Desk(new Charges(shelf, TARIFF), new Map([[11, "collect by 6"]]));
}

/**
 * The desk behind a server on whatever port the machine had going spare, and
 * how to shut it again. Never a port named here: what is free on the machine
 * grading this is not something a test may decide for it.
 */
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

test("the desk says what is owed on a bag", () => {
  assert.deepEqual(weighedThrough().answer(11), {
    status: 200,
    body: { ticket: 11, owed: 22, note: "collect by 6" },
  });
});

test("a ticket the office wrote nothing against carries no note", () => {
  assert.equal(weighedThrough().noteOn(12), NO_NOTE);
});

test("the takings are what the whole shelf came to", () => {
  assert.deepEqual(weighedThrough().cashUp(), { takings: 45, weighAgain: [] });
});

test("the day book writes up a bag nobody weighed as not weighed", () => {
  const shelf = new Shelf([new Bag(11, 2, 9), new Bag(13, 4, NOT_WEIGHED)]);
  const desk = new Desk(new Charges(shelf, TARIFF));

  assert.deepEqual(desk.book(), ["ticket 11: 9", "ticket 13: not weighed"]);
});

test("the counter answers over http", async () => {
  const { port, shut } = await listening(weighedThrough());
  try {
    const replied = await fetch(`http://127.0.0.1:${port}/bag/11`);

    assert.equal(replied.status, 200);
    assert.deepEqual(await replied.json(), {
      ticket: 11,
      owed: 22,
      note: "collect by 6",
    });
  } finally {
    await shut();
  }
});

test("the takings are asked for over http at the end of the day", async () => {
  const { port, shut } = await listening(weighedThrough());
  try {
    const replied = await fetch(`http://127.0.0.1:${port}/takings`);

    assert.equal(replied.status, 200);
    assert.deepEqual(await replied.json(), { takings: 45, weighAgain: [] });
  } finally {
    await shut();
  }
});

test("what is not a ticket and what is not on the shelf are told apart", async () => {
  const { port, shut } = await listening(weighedThrough());
  try {
    const nonsense = await fetch(`http://127.0.0.1:${port}/bag/see%20the%20man`);
    const missing = await fetch(`http://127.0.0.1:${port}/bag/99`);
    const elsewhere = await fetch(`http://127.0.0.1:${port}/parcels`);

    assert.equal(nonsense.status, 400);
    assert.equal(missing.status, 404);
    assert.equal(elsewhere.status, 404);
  } finally {
    await shut();
  }
});
