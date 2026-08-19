/**
 * Held out: what stands on the page at the end of a night several boats came
 * up on.
 *
 * The agent never sees this file. It asserts what the lockhouse *ends the
 * night with* and not how it gets there: where a boat is put behind the one
 * in the chamber is the fix's own business, and any repair that has every
 * boat worked through and written up in the order it came passes here.
 *
 * Nothing here waits on a length of time, and nothing here is a fact about
 * how fast the machine grading it happens to be. Every verdict is read off a
 * settled promise and a recorded sequence: the night hands back a promise
 * that settles when the work is done, and the page is a list in the order it
 * was written. A test that slept and then looked would be a coin toss on the
 * scheduler, and round 1 has already paid for one of those.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Book } from "./book.ts";
import { Keeper, Orders } from "./keeper.ts";
import { A_LOCKING, Lock, Tally } from "./lock.ts";
import { Boat, Cut } from "./water.ts";

const MARK = 30;
const DEEPEST = 9;

const SALLY = new Boat("Sally", 20, 8);
const KINGFISHER = new Boat("Kingfisher", 14, 6);
const BITTERN = new Boat("Bittern", 30, 12);
const EMILY_JANE = new Boat("Emily Jane", 18);

/** A night at the lockhouse, and everything that can be asked about it after. */
function tonight(): {
  cut: Cut;
  book: Book;
  lock: Lock;
  tally: Tally;
  keeper: Keeper;
} {
  const cut = new Cut();
  const book = new Book();
  const lock = new Lock(cut, MARK);
  const tally = new Tally(cut);
  const keeper = new Keeper(cut, lock, book, new Orders(DEEPEST));
  return { cut, book, lock, tally, keeper };
}

/** Four boats up one behind another, and the cut shut behind them. */
function fourCameUp(cut: Cut): void {
  for (const boat of [SALLY, KINGFISHER, BITTERN, EMILY_JANE]) {
    cut.aBoat(boat);
  }
  cut.shutting();
}

const THE_NIGHT = [
  `Sally: 8, ${A_LOCKING + 20} minutes`,
  `Kingfisher: 6, ${A_LOCKING + 14} minutes`,
  "Bittern: turned back",
  "Emily Jane: turned back",
];

test("every boat that came up is on the page, in the order it came", async () => {
  const { cut, keeper } = tonight();

  const night = keeper.keep();
  fourCameUp(cut);

  assert.deepEqual(await night, THE_NIGHT);
});

test("the boats behind the first one are worked through, not dropped", async () => {
  const { cut, lock, keeper } = tonight();

  const night = keeper.keep();
  fourCameUp(cut);
  await night;

  assert.equal(lock.worked(), 2);
  assert.equal(keeper.drew(), 2);
});

test("what the night hands back is the page as it stands when it is done", async () => {
  const { cut, book, keeper } = tonight();

  const night = keeper.keep();
  fourCameUp(cut);
  const page = await night;

  assert.deepEqual(page, book.read());
  assert.equal(page.length, 4);
});

test("the tally and the page say the same thing about the night", async () => {
  const { cut, tally, keeper } = tonight();

  const night = keeper.keep();
  fourCameUp(cut);

  assert.equal((await night).length, tally.boats());
  assert.equal(tally.shutUp(), true);
});

test("a boat that came up second is written up second", async () => {
  const { cut, keeper } = tonight();

  const night = keeper.keep();
  cut.aBoat(BITTERN);
  cut.aBoat(SALLY);
  cut.shutting();

  assert.deepEqual(await night, [
    "Bittern: turned back",
    `Sally: 8, ${A_LOCKING + 20} minutes`,
  ]);
});

test("a night one boat came up on reads exactly as it did before", async () => {
  const { cut, keeper } = tonight();

  const night = keeper.keep();
  cut.aBoat(SALLY);
  cut.shutting();

  assert.deepEqual(await night, [`Sally: 8, ${A_LOCKING + 20} minutes`]);
});
