import test from "node:test";
import assert from "node:assert/strict";

import { hoursIn, whoHadIt } from "./spells.ts";

const WORKED = [
  { burner: "Trewin", from: 1, to: 6 },
  { burner: "Roskilly", from: 7, to: 11 },
];

test("a spell is as long as the hours it ran, both ends counted", () => {
  assert.equal(hoursIn(WORKED[0]), 6);
  assert.equal(hoursIn({ burner: "Penhale", from: 12, to: 12 }), 1);
});

test("the burner who had the kiln at an hour is the one whose spell it fell in", () => {
  assert.equal(whoHadIt(WORKED, 1), "Trewin");
  assert.equal(whoHadIt(WORKED, 6), "Trewin");
  assert.equal(whoHadIt(WORKED, 7), "Roskilly");
  assert.equal(whoHadIt(WORKED, 12), null);
});
