/**
 * Held out: the behaviour half. What the court says must not change, however
 * it comes to say it — so every line of this file passes on the pristine
 * repository and has to go on passing once the verdicts are on a table.
 *
 * Nothing here reads the table or names it. It puts bylaws before the court
 * and reads what comes back: the words tried in their own context, the
 * findings and nothing else in scope, the ruling on each verdict the court
 * knows, the ruling on one it does not, and what a sitting comes to.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Bylaw, readOff } from "./bylaws.ts";
import { Case, readCase } from "./cases.ts";
import { Court, NOTHING_TO_ANSWER, UNKNOWN_VERDICT } from "./court.ts";

const STOW = new Court("stow");
const BOOK = readOff(
  [
    "overstint | beasts > stint | amercement | 12",
    "hedgebote | fenced === false | pain | 40",
    "waste | timber > 0 | distraint | 0",
  ].join("\n"),
);
const WILLIAM = readCase("william-mason: beasts=12 stint=8 fenced=no timber=2");
const AGNES = readCase("agnes-fuller: beasts=4 stint=8 fenced=yes timber=0");

test("the words are tried against the findings and nothing else", () => {
  assert.equal(STOW.broken(BOOK[0], WILLIAM), true);
  assert.equal(STOW.broken(BOOK[0], AGNES), false);
  // Nothing of the manor's is in scope inside the parish's words.
  const prying = new Bylaw("prying", "typeof process === 'object'", "amercement", 12);
  assert.equal(STOW.broken(prying, WILLIAM), false);
});

test("words that will not run leave the case with nothing to answer", () => {
  for (const words of ["beasts.graze(", "swine > stint", "throw new Error('no')"]) {
    const bylaw = new Bylaw("odd", words, "amercement", 12);

    assert.equal(STOW.broken(bylaw, WILLIAM), false);
    assert.equal(STOW.rule(bylaw, WILLIAM).said, NOTHING_TO_ANSWER);
  }
});

test("each verdict the court knows says exactly what it said before", () => {
  assert.deepEqual(STOW.sitting(BOOK, WILLIAM), [
    { bylaw: "overstint", said: "amerced 12d", pence: 12 },
    { bylaw: "hedgebote", said: "on pain of 40d", pence: 0 },
    { bylaw: "waste", said: "distrained until it is put right", pence: 0 },
  ]);
});

test("a case that answers to nothing in the book answers to nothing", () => {
  assert.deepEqual(STOW.sitting(BOOK, AGNES), [
    { bylaw: "overstint", said: NOTHING_TO_ANSWER, pence: 0 },
    { bylaw: "hedgebote", said: NOTHING_TO_ANSWER, pence: 0 },
    { bylaw: "waste", said: NOTHING_TO_ANSWER, pence: 0 },
  ]);
  assert.equal(STOW.amerced(BOOK, AGNES), 0);
});

test("a verdict the court has never heard of is still said to be none", () => {
  const strange = new Bylaw("strange", "beasts > stint", "banishment", 12);

  assert.deepEqual(STOW.rule(strange, WILLIAM), {
    bylaw: "strange",
    said: UNKNOWN_VERDICT,
    pence: 0,
  });
});

test("an unheard-of verdict is still nothing to answer where nothing is broken", () => {
  const strange = new Bylaw("strange", "beasts > stint", "banishment", 12);

  assert.equal(STOW.rule(strange, AGNES).said, NOTHING_TO_ANSWER);
});

test("the sitting keeps the book's order, and the amercements add up", () => {
  const twice = [...BOOK, ...BOOK];

  assert.deepEqual(
    STOW.sitting(twice, WILLIAM).map((ruling) => ruling.bylaw),
    ["overstint", "hedgebote", "waste", "overstint", "hedgebote", "waste"],
  );
  assert.equal(STOW.amerced(twice, WILLIAM), 24);
  assert.equal(STOW.amerced([], WILLIAM), 0);
});

test("a bylaw the pence go with pays those pence and no others", () => {
  const dearer = new Bylaw("overstint", "beasts > stint", "amercement", 30);

  assert.deepEqual(STOW.rule(dearer, WILLIAM), {
    bylaw: "overstint",
    said: "amerced 30d",
    pence: 30,
  });
});
