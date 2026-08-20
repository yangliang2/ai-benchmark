/**
 * Held out: what the seals say about a register a later hand has been at.
 *
 * The agent never sees this file. It never says what a seal is *of* — the
 * recipe is the solution's own, and pinning one here would make this a
 * transcription rather than a feature. What it holds to is what a chain has to
 * do to be one: a seal that depends on both what stands before it and every
 * word of the entry, and a register that can say where the seals somebody
 * wrote down stop agreeing with the entries in front of it.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Entry } from "./entries.ts";
import { Register, sealFor } from "./register.ts";
import { SEAL_WIDTH, THE_FIRST_SEAL } from "./seals.ts";

const LENT = [
  new Entry("14 March 1832", "Hannah Skerrett, buried", "J. Pring"),
  new Entry("19 March 1832", "Thomas Vole and Ann Dyke, married", "J. Pring"),
  new Entry("2 April 1832", "Susannah Vole, baptised", "R. Membury"),
];

/** The register as the clerk closed it, and the seals he wrote down that day. */
function asTheClerkClosedIt(): { register: Register; wroteDown: string[] } {
  const register = new Register(LENT);
  return { register, wroteDown: register.seals() };
}

/** The same register with a later hand through the second entry. */
function aLaterHand(): Register {
  return new Register([LENT[0], LENT[1].saying("Thomas Vole and Ann Dyke, of this parish, married"), LENT[2]]);
}

test("a seal is a seal, of the width the wax is written in", () => {
  const seal = sealFor(THE_FIRST_SEAL, LENT[0]);

  assert.equal(seal.length, SEAL_WIDTH);
  assert.match(seal, /^[0-9a-f]+$/);
  assert.equal(seal, sealFor(THE_FIRST_SEAL, LENT[0]));
});

test("a seal turns on what stands before it and on every word of the entry", () => {
  const seal = sealFor(THE_FIRST_SEAL, LENT[0]);

  assert.notEqual(seal, sealFor(sealFor(THE_FIRST_SEAL, LENT[1]), LENT[0]));
  assert.notEqual(seal, sealFor(THE_FIRST_SEAL, LENT[0].saying("Hannah Skerrett, buryed")));
  assert.notEqual(
    sealFor(THE_FIRST_SEAL, LENT[0]),
    sealFor(THE_FIRST_SEAL, new Entry(LENT[0].on, LENT[0].what, "R. Membury")),
  );
});

test("the register seals one entry onto the seal standing before it", () => {
  const { register, wroteDown } = asTheClerkClosedIt();

  assert.equal(wroteDown.length, 3);
  assert.equal(wroteDown[0], sealFor(THE_FIRST_SEAL, LENT[0]));
  assert.equal(wroteDown[1], sealFor(wroteDown[0], LENT[1]));
  assert.equal(wroteDown[2], sealFor(wroteDown[1], LENT[2]));
  assert.equal(register.seal(), wroteDown[2]);
});

test("a register holding nothing stands at what stands before anything", () => {
  const empty = new Register();

  assert.deepEqual(empty.seals(), []);
  assert.equal(empty.seal(), THE_FIRST_SEAL);
  assert.equal(empty.brokenAt([]), null);
});

test("nothing is broken in a register nobody has been at", () => {
  const { register, wroteDown } = asTheClerkClosedIt();

  assert.equal(register.brokenAt(wroteDown), null);
  assert.equal(register.brokenAt(register.seals()), null);
});

test("a later hand through one entry breaks the seal at that place", () => {
  const { wroteDown } = asTheClerkClosedIt();

  assert.equal(aLaterHand().brokenAt(wroteDown), 2);
});

test("what came after a later hand is unputbackable", () => {
  const { register } = asTheClerkClosedIt();
  const altered = aLaterHand();

  assert.equal(altered.seals()[0], register.seals()[0]);
  assert.notEqual(altered.seals()[2], register.seals()[2]);
  assert.notEqual(altered.seal(), register.seal());
});

test("an entry slipped in is broken at the place it was slipped in at", () => {
  const { wroteDown } = asTheClerkClosedIt();
  const slipped = new Register([
    LENT[0],
    new Entry("17 March 1832", "Mary Kellow, baptised", "J. Pring"),
    LENT[1],
    LENT[2],
  ]);

  assert.equal(slipped.brokenAt(wroteDown), 2);
});

test("an entry made since the seals were written down is past the end of them", () => {
  const { register, wroteDown } = asTheClerkClosedIt();
  const since = register.entered(new Entry("5 April 1832", "John Kellow, buried", "R. Membury"));

  assert.equal(since.brokenAt(wroteDown), 4);
});

test("a page torn out is past the end of the entries", () => {
  const { wroteDown } = asTheClerkClosedIt();
  const torn = new Register([LENT[0], LENT[1]]);

  assert.equal(torn.brokenAt(wroteDown), 3);
});

test("what the register already did it does exactly as before", () => {
  const { register } = asTheClerkClosedIt();

  assert.equal(register.count(), 3);
  assert.equal(register.at(2)?.by, "J. Pring");
  assert.deepEqual(register.asWritten(), [
    "14 March 1832 | Hannah Skerrett, buried | J. Pring",
    "19 March 1832 | Thomas Vole and Ann Dyke, married | J. Pring",
    "2 April 1832 | Susannah Vole, baptised | R. Membury",
  ]);
  assert.equal(register.entered(LENT[0]).count(), 4);
});
