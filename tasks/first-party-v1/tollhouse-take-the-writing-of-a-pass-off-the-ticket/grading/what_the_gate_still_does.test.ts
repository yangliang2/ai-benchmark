/**
 * Held out: the behaviour half. What the gate does must not change, wherever
 * the writing of a pass ends up living — so every line of this file passes on
 * the pristine repository and has to go on passing afterwards.
 *
 * Everything here goes through the gate and through the table, which are the
 * two surfaces the restructuring leaves standing: the exact link a pass is
 * written as, what reads back off one, what the keeper may ask for, and what
 * he may not.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Gate, NOTHING_TO_ASK } from "./gate.ts";
import { Ticket } from "./tickets.ts";
import { LADEN, NOT_ON_THE_TABLE, classes, tollFor } from "./tolls.ts";

const WESTGATE = new Gate("westgate");
const EASTGATE = new Gate("eastgate");

test("a pass is still written as the same link, word for word", () => {
  assert.equal(
    WESTGATE.write(new Ticket("westgate", "cart", 2, false)),
    "toll://westgate/pass?traffic=cart&axles=2&laden=no",
  );
  assert.equal(
    WESTGATE.write(new Ticket("westgate", "drove", 1, true)),
    "toll://westgate/pass?traffic=drove&axles=1&laden=yes",
  );
});

test("a pass written anywhere reads back the same everywhere", () => {
  const ticket = new Ticket("eastgate", "waggon", 6, true);
  const link = EASTGATE.write(ticket);

  assert.deepEqual(EASTGATE.readBack(link), ticket);
  assert.deepEqual(WESTGATE.readBack(link), ticket);
});

test("what is not a pass reads back as no pass at all", () => {
  for (const handed of [
    "",
    "a scrap of paper",
    "toll://westgate/pass",
    "toll://westgate/pass?traffic=cart&laden=no",
    "toll://westgate/pass?traffic=cart&axles=two&laden=no",
    "toll://westgate/pass?traffic=cart&axles=2&laden=perhaps",
    "toll://westgate/turnpike?traffic=cart&axles=2&laden=no",
    "https://westgate/pass?traffic=cart&axles=2&laden=no",
  ]) {
    assert.equal(WESTGATE.readBack(handed), NOTHING_TO_ASK, handed);
    assert.equal(WESTGATE.charge(handed), NOTHING_TO_ASK, handed);
  }
});

test("the keeper asks the table's figure and no other", () => {
  const laden = new Ticket("westgate", "waggon", 4, true);

  assert.equal(WESTGATE.charge(WESTGATE.write(laden)), tollFor("waggon", 4, true));
  assert.equal(WESTGATE.charge(WESTGATE.write(laden)), 4 * 6 + LADEN);
});

test("a pass is good at the gate whose name is on it and nowhere else", () => {
  const link = EASTGATE.write(new Ticket("eastgate", "cart", 2, false));

  assert.equal(EASTGATE.charge(link), 8);
  assert.equal(WESTGATE.charge(link), NOTHING_TO_ASK);
});

test("traffic the table does not name is not a free pass through the gate", () => {
  const link = WESTGATE.write(new Ticket("westgate", "traction-engine", 4, false));

  assert.equal(WESTGATE.charge(link), NOT_ON_THE_TABLE);
  assert.deepEqual(classes(), ["cart", "waggon", "gig", "drove"]);
});

test("the day's takings are what the keeper could ask for and no more", () => {
  const handedIn = [
    WESTGATE.write(new Ticket("westgate", "waggon", 4, true)),
    WESTGATE.write(new Ticket("westgate", "gig", 2, false)),
    WESTGATE.write(new Ticket("westgate", "traction-engine", 4, false)),
    EASTGATE.write(new Ticket("eastgate", "cart", 2, false)),
    "a scrap of paper",
  ];

  assert.equal(WESTGATE.takings(handedIn), 26 + 6);
  assert.equal(WESTGATE.takings([]), 0);
});
