import test from "node:test";
import assert from "node:assert/strict";

import {
  CANNOT_SAY,
  Charges,
  NOTHING_OWED,
  NOTHING_PAID,
  Tariff,
} from "./charges.ts";
import { Bag, NOT_WEIGHED, Shelf } from "./shelf.ts";

const TARIFF = new Tariff(2, 1);

const SHELF = new Shelf([
  new Bag(11, 2, 9, "Mrs Dando"),
  new Bag(12, 1, 21),
  new Bag(13, 4, NOT_WEIGHED, "the man off the 8.40"),
]);

test("the tariff charges by the day and by the kilo", () => {
  assert.equal(TARIFF.forStay(SHELF.bagFor(11)), 22);
  assert.equal(TARIFF.forStay(SHELF.bagFor(12)), 23);
});

test("a bag left and fetched the same day costs nothing", () => {
  assert.equal(TARIFF.forStay(new Bag(14, 0, 3)), NOTHING_OWED);
});

test("the tariff cannot say what a bag nobody weighed comes to", () => {
  assert.equal(TARIFF.forStay(SHELF.bagFor(13)), CANNOT_SAY);
});

test("the tariff cannot say for a ticket with nothing against it", () => {
  assert.equal(TARIFF.forStay(SHELF.bagFor(99)), CANNOT_SAY);
});

test("what is owed on a bag is what the tariff makes of it", () => {
  const charges = new Charges(SHELF, TARIFF);

  assert.equal(charges.owedOn(11), 22);
  assert.equal(charges.owedOn(12), 23);
});

test("the tickets standing against a run are the shelf's own", () => {
  assert.deepEqual(new Charges(SHELF, TARIFF).ticketed(), [11, 12, 13]);
});

test("nothing has been paid on a bag nobody has paid on", () => {
  const charges = new Charges(SHELF, TARIFF, new Map([[11, 5]]));

  assert.equal(charges.paidOn(11), 5);
  assert.equal(charges.paidOn(12), NOTHING_PAID);
});

test("what is still owing is what is owed less what is paid", () => {
  const charges = new Charges(SHELF, TARIFF, new Map([[11, 5]]));

  assert.equal(charges.stillToPay(11), 17);
  assert.equal(charges.stillToPay(12), 23);
});
