import test from "node:test";
import assert from "node:assert/strict";

import { Bylaw } from "./bylaws.ts";
import { Case } from "./cases.ts";
import { Court, NOTHING_TO_ANSWER, UNKNOWN_VERDICT } from "./court.ts";

const STOW = new Court("stow");
const OVERSTINT = new Bylaw("overstint", "beasts > stint", "amercement", 12);
const HEDGEBOTE = new Bylaw("hedgebote", "fenced === false", "pain", 40);
const WASTE = new Bylaw("waste", "timber > 0", "distraint", 0);
const WILLIAM = new Case("william-mason", { beasts: 12, stint: 8, fenced: false, timber: 2 });
const AGNES = new Case("agnes-fuller", { beasts: 4, stint: 8, fenced: true, timber: 0 });

test("the court tries the parish's words against what the jury found", () => {
  assert.equal(STOW.broken(OVERSTINT, WILLIAM), true);
  assert.equal(STOW.broken(OVERSTINT, AGNES), false);
});

test("words that will not run are words the case does not answer to", () => {
  const nonsense = new Bylaw("nonsense", "beasts.graze(", "amercement", 12);
  const unknown = new Bylaw("unknown", "swine > stint", "amercement", 12);

  assert.equal(STOW.broken(nonsense, WILLIAM), false);
  assert.equal(STOW.broken(unknown, WILLIAM), false);
});

test("a bylaw the case does not answer to is nothing to answer", () => {
  assert.deepEqual(STOW.rule(OVERSTINT, AGNES), {
    bylaw: "overstint",
    said: NOTHING_TO_ANSWER,
    pence: 0,
  });
});

test("an amercement takes the bylaw's pence", () => {
  assert.deepEqual(STOW.rule(OVERSTINT, WILLIAM), {
    bylaw: "overstint",
    said: "amerced 12d",
    pence: 12,
  });
});

test("a pain takes nothing yet, and says what it will take", () => {
  assert.deepEqual(STOW.rule(HEDGEBOTE, WILLIAM), {
    bylaw: "hedgebote",
    said: "on pain of 40d",
    pence: 0,
  });
});

test("a distraint takes nothing and holds the thing itself", () => {
  assert.deepEqual(STOW.rule(WASTE, WILLIAM), {
    bylaw: "waste",
    said: "distrained until it is put right",
    pence: 0,
  });
});

test("a verdict the court has never heard of is said to be none", () => {
  const strange = new Bylaw("strange", "beasts > stint", "banishment", 12);

  assert.deepEqual(STOW.rule(strange, WILLIAM), {
    bylaw: "strange",
    said: UNKNOWN_VERDICT,
    pence: 0,
  });
});

test("the sitting goes through the book in order, and the amercements add up", () => {
  const book = [OVERSTINT, HEDGEBOTE, WASTE];

  assert.deepEqual(
    STOW.sitting(book, WILLIAM).map((ruling) => ruling.bylaw),
    ["overstint", "hedgebote", "waste"],
  );
  assert.equal(STOW.amerced(book, WILLIAM), 12);
  assert.equal(STOW.amerced(book, AGNES), 0);
});
