import test from "node:test";
import assert from "node:assert/strict";

import { KINDS, Stone, Yard, standing } from "./stones.ts";

const HEWN = [
  new Stone("A1", "slate", 30),
  new Stone("b2", "limestone", 42),
  new Stone("C3", "granite", 36),
];

test("the yard holds its stones in the order they were rough-hewn", () => {
  const yard = new Yard(HEWN);

  assert.deepEqual(
    yard.stones().map((stone) => stone.mark),
    ["A1", "b2", "C3"],
  );
  assert.equal(yard.count(), 3);
});

test("a stone is found however its mark was chalked", () => {
  const yard = new Yard(HEWN);

  assert.equal(standing(yard, " B2 ")?.kind, "limestone");
  assert.equal(standing(yard, "c3")?.inches, 36);
  assert.equal(standing(yard, "D4"), null);
});

test("rough-hewing one more leaves the yard it was standing in alone", () => {
  const yard = new Yard(HEWN);
  const after = yard.hewn(new Stone("D4", "slate", 24));

  assert.equal(after.count(), 4);
  assert.equal(yard.count(), 3);
  assert.equal(KINDS[0], "slate");
});
