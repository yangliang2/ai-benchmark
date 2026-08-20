import test from "node:test";
import assert from "node:assert/strict";

import { Bylaw, NOT_A_BYLAW, readBylaw, readOff } from "./bylaws.ts";

const OVERSTINT = new Bylaw("overstint", "beasts > stint", "amercement", 12);
const HEDGEBOTE = new Bylaw("hedgebote", "fenced === false", "pain", 40);

test("a bylaw reads off one line of the book", () => {
  assert.deepEqual(readBylaw("overstint | beasts > stint | amercement | 12"), OVERSTINT);
});

test("a line nobody can read is not a bylaw", () => {
  assert.equal(readBylaw(""), NOT_A_BYLAW);
  assert.equal(readBylaw("overstint | beasts > stint"), NOT_A_BYLAW);
  assert.equal(readBylaw("overstint | beasts > stint | amercement | some"), NOT_A_BYLAW);
});

test("a page reads off in the order it was written up, blots left out", () => {
  const page = [
    "overstint | beasts > stint | amercement | 12",
    "a blot",
    "hedgebote | fenced === false | pain | 40",
  ].join("\n");

  assert.deepEqual(readOff(page), [OVERSTINT, HEDGEBOTE]);
});
