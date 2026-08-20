import test from "node:test";
import assert from "node:assert/strict";

import { Account, LETTERS_TO_A_HUNDRED, PENCE_TO_A_SHILLING, Piece, Rate } from "./account.ts";
import { Stone } from "./stones.ts";

const RATE = new Rate(7, 30);
const SLAB = new Stone("A1", "slate", 30);
const HUNDRED = "A".repeat(LETTERS_TO_A_HUNDRED);

test("a stone is charged by the inch", () => {
  assert.equal(RATE.forStone(SLAB), 210);
  assert.equal(RATE.forStone(new Stone("b2", "limestone", 1)), 7);
});

test("a part hundred of lettering is not charged for at all", () => {
  assert.equal(RATE.forLetters(HUNDRED), 30);
  assert.equal(RATE.forLetters(`${HUNDRED}${HUNDRED}`), 60);
  assert.equal(RATE.forLetters("HANNAH SKERRETT 1832"), 0);
  assert.equal(RATE.forLetters(`${HUNDRED}AND ANOTHER FEW`), 30);
});

test("a line of an account is the stone and the lettering, in pence", () => {
  const account = new Account(RATE)
    .setDown(new Piece(SLAB, "HANNAH SKERRETT 1832"))
    .setDown(new Piece(new Stone("b2", "limestone", 42), HUNDRED));

  assert.deepEqual(account.lines(), [210, 324]);
  assert.equal(PENCE_TO_A_SHILLING, 12);
});

test("setting a piece down leaves the account it was set down on alone", () => {
  const account = new Account(RATE);
  const after = account.setDown(new Piece(SLAB, "HANNAH SKERRETT 1832"));

  assert.deepEqual(account.lines(), []);
  assert.deepEqual(after.lines(), [210]);
});
