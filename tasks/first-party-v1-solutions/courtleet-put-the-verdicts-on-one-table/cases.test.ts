import test from "node:test";
import assert from "node:assert/strict";

import { Case, NOT_A_CASE, asFact, readCase } from "./cases.ts";

test("a finding is a number, a yes or no, or a word", () => {
  assert.equal(asFact("12"), 12);
  assert.equal(asFact("-3"), -3);
  assert.equal(asFact("yes"), true);
  assert.equal(asFact("no"), false);
  assert.equal(asFact("michaelmas"), "michaelmas");
});

test("a presentment reads off one line of the roll", () => {
  assert.deepEqual(
    readCase("william-mason: beasts=12 stint=8 fenced=no"),
    new Case("william-mason", { beasts: 12, stint: 8, fenced: false }),
  );
});

test("a line nobody can read is not a presentment", () => {
  assert.equal(readCase(""), NOT_A_CASE);
  assert.equal(readCase("william-mason"), NOT_A_CASE);
  assert.equal(readCase("william-mason: beasts"), NOT_A_CASE);
});
