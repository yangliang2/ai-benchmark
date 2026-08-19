import test from "node:test";
import assert from "node:assert/strict";

import { A_LOCKING, Lock, Tally } from "./lock.ts";
import { Boat, Cut } from "./water.ts";

const MARK = 30;

test("working a boat through settles when it is out at the far end", async () => {
  const cut = new Cut();
  const lock = new Lock(cut, MARK);

  const minutes = await lock.through(new Boat("Sally", 20, 8));

  assert.equal(minutes, A_LOCKING + 20);
  assert.equal(lock.stands(), MARK);
  assert.equal(lock.worked(), 1);
});

test("boats go through the chamber one behind another", async () => {
  const cut = new Cut();
  const lock = new Lock(cut, MARK);

  const first = await lock.through(new Boat("Sally", 20, 8));
  const second = await lock.through(new Boat("Kingfisher", 14, 6));

  assert.deepEqual([first, second], [A_LOCKING + 20, A_LOCKING + 14]);
  assert.equal(lock.worked(), 2);
});

test("the tally counts every boat that came up to the gate", () => {
  const cut = new Cut();
  const tally = new Tally(cut);

  cut.aBoat(new Boat("Sally", 20, 8));
  cut.aBoat(new Boat("Kingfisher", 14, 6));
  cut.aBoat(new Boat("Bittern", 30, 12));

  assert.equal(tally.boats(), 3);
  assert.equal(tally.shutUp(), false);
});

test("the tally knows the night has shut", () => {
  const cut = new Cut();
  const tally = new Tally(cut);

  cut.shutting();

  assert.equal(tally.shutUp(), true);
});
