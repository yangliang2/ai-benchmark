import test from "node:test";
import assert from "node:assert/strict";

import { LADEN, NOT_ON_THE_TABLE, classes, tollFor } from "./tolls.ts";

test("the table charges by the axle, by class of traffic", () => {
  assert.equal(tollFor("cart", 2, false), 8);
  assert.equal(tollFor("waggon", 4, false), 24);
  assert.equal(tollFor("gig", 2, false), 6);
  assert.equal(tollFor("drove", 1, false), 2);
});

test("a load that is on costs a little more than one that is off", () => {
  assert.equal(tollFor("cart", 2, true), 8 + LADEN);
});

test("traffic the table does not name is not a free pass", () => {
  assert.equal(tollFor("traction-engine", 4, false), NOT_ON_THE_TABLE);
});

test("traffic on no axles at all is not on the table either", () => {
  assert.equal(tollFor("cart", 0, false), NOT_ON_THE_TABLE);
  assert.equal(tollFor("cart", -2, false), NOT_ON_THE_TABLE);
  assert.equal(tollFor("cart", 1.5, false), NOT_ON_THE_TABLE);
});

test("the table names what it names, in the order it is written up", () => {
  assert.deepEqual(classes(), ["cart", "waggon", "gig", "drove"]);
});
