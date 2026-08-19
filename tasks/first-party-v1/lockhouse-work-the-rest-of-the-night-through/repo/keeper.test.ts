import test from "node:test";
import assert from "node:assert/strict";

import { Book } from "./book.ts";
import { A_LOCKING, Lock } from "./lock.ts";
import { Keeper, Orders } from "./keeper.ts";
import { Boat, Cut } from "./water.ts";

const MARK = 30;
const DEEPEST = 9;

/** A night, its book, and the cut everything reaches it on. */
function tonight(): { cut: Cut; book: Book; keeper: Keeper } {
  const cut = new Cut();
  const book = new Book();
  const keeper = new Keeper(cut, new Lock(cut, MARK), book, new Orders(DEEPEST));
  return { cut, book, keeper };
}

test("the standing orders take a boat that clears the sill", () => {
  const orders = new Orders(DEEPEST);

  assert.equal(orders.willTake(new Boat("Sally", 20, 8)), true);
  assert.equal(orders.willTake(new Boat("Bittern", 30, 12)), false);
});

test("a boat nobody gauged is not let through on a guess", () => {
  assert.equal(new Orders(DEEPEST).willTake(new Boat("Emily Jane", 18)), false);
});

test("one boat, worked through, and duly entered", async () => {
  const { cut, keeper } = tonight();

  const night = keeper.keep();
  cut.aBoat(new Boat("Sally", 20, 8));
  cut.shutting();

  assert.deepEqual(await night, [`Sally: 8, ${A_LOCKING + 20} minutes`]);
});

test("a boat the orders refuse is turned back, and duly entered", async () => {
  const { cut, keeper } = tonight();

  const night = keeper.keep();
  cut.aBoat(new Boat("Bittern", 30, 12));
  cut.shutting();

  assert.deepEqual(await night, ["Bittern: turned back"]);
});

test("a night nothing came up on leaves the page empty", async () => {
  const { cut, keeper } = tonight();

  const night = keeper.keep();
  cut.shutting();

  assert.deepEqual(await night, []);
});

test("the water a boat took is counted against the night", async () => {
  const { cut, keeper } = tonight();

  const night = keeper.keep();
  cut.aBoat(new Boat("Sally", 20, 8));
  cut.shutting();
  await night;

  assert.equal(keeper.drew(), 1);
});

test("what the night hands back is the page as the book has it", async () => {
  const { cut, book, keeper } = tonight();

  const night = keeper.keep();
  cut.aBoat(new Boat("Sally", 20, 8));
  cut.shutting();

  assert.deepEqual(await night, book.read());
});
