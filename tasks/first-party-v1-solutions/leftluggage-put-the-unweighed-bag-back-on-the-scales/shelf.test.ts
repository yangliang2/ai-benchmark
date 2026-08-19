import test from "node:test";
import assert from "node:assert/strict";

import { Bag, NOBODY, NOT_ON_THE_SHELF, NOT_WEIGHED, Shelf } from "./shelf.ts";

const SHELF = new Shelf([
  new Bag(11, 2, 9, "Mrs Dando"),
  new Bag(12, 1, 21),
  new Bag(13, 4, NOT_WEIGHED, "the man off the 8.40"),
]);

test("the shelf keeps its tickets in the order they came in", () => {
  assert.deepEqual(SHELF.ticketed(), [11, 12, 13]);
});

test("a ticket with nothing against it is not on the shelf", () => {
  assert.equal(SHELF.bagFor(99), NOT_ON_THE_SHELF);
});

test("what a bag stood at comes back off the shelf", () => {
  assert.equal(SHELF.weighed(11), 9);
  assert.equal(SHELF.weighed(12), 21);
});

test("a bag nobody wrote a weight down for comes back as not weighed", () => {
  assert.equal(SHELF.weighed(13), NOT_WEIGHED);
  assert.equal(SHELF.weighed(99), NOT_WEIGHED);
});

test("a bag the office took no name for comes back as nobody", () => {
  assert.equal(SHELF.leftBy(11), "Mrs Dando");
  assert.equal(SHELF.leftBy(12), NOBODY);
});
