import test from "node:test";
import assert from "node:assert/strict";

import { Bank, Kiln, STONE, marked } from "./kilns.ts";

const BUILT = [
  new Kiln("TOP", "chalk", 300),
  new Kiln("mid", "limestone", 420),
  new Kiln("Low", "clunch", 360),
];

test("the bank holds its kilns in the order they were built", () => {
  const bank = new Bank(BUILT);

  assert.deepEqual(
    bank.kilns().map((kiln) => kiln.mark),
    ["TOP", "mid", "Low"],
  );
  assert.equal(bank.count(), 3);
});

test("a kiln is found however its mark was cut", () => {
  const bank = new Bank(BUILT);

  assert.equal(marked(bank, " Mid ")?.stone, "limestone");
  assert.equal(marked(bank, "low")?.holds, 360);
  assert.equal(marked(bank, "OLD"), null);
});

test("building one more leaves the bank it was built into alone", () => {
  const bank = new Bank(BUILT);
  const after = bank.built(new Kiln("New", "chalk", 240));

  assert.equal(after.count(), 4);
  assert.equal(bank.count(), 3);
  assert.equal(STONE[0], "chalk");
});
