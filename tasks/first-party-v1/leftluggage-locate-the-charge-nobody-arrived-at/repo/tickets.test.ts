import test from "node:test";
import assert from "node:assert/strict";

import { NOT_A_TICKET, NOT_WEIGHED_UP, numberOf, writtenUp } from "./tickets.ts";

test("a ticket is read off however it was written down", () => {
  assert.equal(numberOf("12"), 12);
  assert.equal(numberOf("  12 "), 12);
  assert.equal(numberOf("#12"), 12);
});

test("what nobody can read off is not ticket nought", () => {
  assert.equal(numberOf("see the man"), NOT_A_TICKET);
  assert.equal(numberOf(""), NOT_A_TICKET);
  assert.equal(numberOf("12a"), NOT_A_TICKET);
});

test("a bag is written up with what it stood at", () => {
  assert.equal(writtenUp(12, 9), "ticket 12: 9");
});

test("a bag nobody weighed is written up as not weighed", () => {
  assert.equal(writtenUp(12, null), `ticket 12: ${NOT_WEIGHED_UP}`);
});
