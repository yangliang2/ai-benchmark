import test from "node:test";
import assert from "node:assert/strict";

import { SEAL_WIDTH, THE_FIRST_SEAL, sealOf } from "./seals.ts";

test("a seal is hex of the one width, whatever it was taken over", () => {
  for (const text of ["", "a", "the whole of the parish register"]) {
    assert.match(sealOf(text), /^[0-9a-f]+$/);
    assert.equal(sealOf(text).length, SEAL_WIDTH);
  }
});

test("the same text seals the same way every time", () => {
  assert.equal(sealOf("J. Pring"), sealOf("J. Pring"));
});

test("a different text seals differently", () => {
  assert.notEqual(sealOf("J. Pring"), sealOf("J. Prlng"));
});

test("what stands before the first entry is nothing sealed at all", () => {
  assert.equal(THE_FIRST_SEAL.length, SEAL_WIDTH);
  assert.notEqual(THE_FIRST_SEAL, sealOf(""));
});
