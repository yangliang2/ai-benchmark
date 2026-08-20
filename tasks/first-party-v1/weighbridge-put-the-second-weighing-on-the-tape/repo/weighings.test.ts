import test from "node:test";
import assert from "node:assert/strict";

import { HAULIER_WIDTH, Weighing, asWritten } from "./weighings.ts";

const LOAD = new Weighing(4021, "Pargeter", 18400, 7250);

test("what the load came to is loaded less empty", () => {
  assert.equal(LOAD.netKg(), 11150);
});

test("a weighing put right keeps its ticket and its haulier", () => {
  const right = LOAD.at(18900, 7250);

  assert.equal(right.ticket, 4021);
  assert.equal(right.haulier, "Pargeter");
  assert.equal(right.netKg(), 11650);
  assert.equal(LOAD.netKg(), 11150);
});

test("a haulier's name is trimmed and cut to what the tape has room for", () => {
  assert.equal(asWritten("  Pargeter  "), "Pargeter");
  assert.equal(asWritten("Braddock and Sons").length, HAULIER_WIDTH);
  assert.equal(asWritten("Braddock and Sons"), "Braddock");
  assert.equal(asWritten("Kyte"), "Kyte");
});
