import test from "node:test";
import assert from "node:assert/strict";

import { Gate, NOTHING_TO_ASK } from "./gate.ts";
import { Ticket } from "./tickets.ts";

const WESTGATE = new Gate("westgate");
const A_WAGGON = new Ticket("westgate", "waggon", 4, true);

test("the keeper writes a pass out as a link", () => {
  assert.equal(
    WESTGATE.write(A_WAGGON),
    "toll://westgate/pass?traffic=waggon&axles=4&laden=yes",
  );
});

test("a pass written at the gate reads back at the gate", () => {
  assert.deepEqual(WESTGATE.readBack(WESTGATE.write(A_WAGGON)), A_WAGGON);
});

test("the keeper asks what the table says on a pass handed in", () => {
  assert.equal(WESTGATE.charge(WESTGATE.write(A_WAGGON)), 26);
});

test("a pass written for another gate is nothing to ask for here", () => {
  const eastgate = new Gate("eastgate");

  assert.equal(WESTGATE.charge(eastgate.write(new Ticket("eastgate", "cart", 2, false))), NOTHING_TO_ASK);
});

test("what is not a pass at all is nothing to ask for", () => {
  assert.equal(WESTGATE.charge("a scrap of paper"), NOTHING_TO_ASK);
  assert.equal(WESTGATE.charge("toll://westgate/pass"), NOTHING_TO_ASK);
  assert.equal(WESTGATE.readBack("toll://westgate/somewhere-else?traffic=cart&axles=2&laden=no"), NOTHING_TO_ASK);
});

test("the day's takings are what the keeper could ask for and no more", () => {
  const eastgate = new Gate("eastgate");
  const handedIn = [
    WESTGATE.write(A_WAGGON),
    WESTGATE.write(new Ticket("westgate", "drove", 1, false)),
    WESTGATE.write(new Ticket("westgate", "traction-engine", 4, false)),
    eastgate.write(new Ticket("eastgate", "cart", 2, false)),
    "a scrap of paper",
  ];

  assert.equal(WESTGATE.takings(handedIn), 28);
});
