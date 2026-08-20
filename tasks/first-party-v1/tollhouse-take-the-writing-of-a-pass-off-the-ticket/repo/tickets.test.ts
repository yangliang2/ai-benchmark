import test from "node:test";
import assert from "node:assert/strict";

import { Ticket } from "./tickets.ts";
import { NOT_ON_THE_TABLE } from "./tolls.ts";

test("a pass says what is owed on the traffic it stands for", () => {
  assert.equal(new Ticket("westgate", "waggon", 4, true).owed(), 26);
  assert.equal(new Ticket("westgate", "gig", 2, false).owed(), 6);
});

test("a pass for traffic the table does not name owes nothing it can name", () => {
  const ticket = new Ticket("westgate", "traction-engine", 4, false);

  assert.equal(ticket.owed(), NOT_ON_THE_TABLE);
  assert.equal(ticket.onTheTable(), false);
});

test("a pass the table has a figure for says so", () => {
  assert.equal(new Ticket("westgate", "cart", 2, false).onTheTable(), true);
});
