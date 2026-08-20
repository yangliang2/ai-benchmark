import test from "node:test";
import assert from "node:assert/strict";

import { Entry } from "./entries.ts";
import { NOTHING_THERE, Register } from "./register.ts";

const LENT = [
  new Entry("14 March 1832", "Hannah Skerrett, buried", "J. Pring"),
  new Entry("19 March 1832", "Thomas Vole and Ann Dyke, married", "J. Pring"),
  new Entry("2 April 1832", "Susannah Vole, baptised", "R. Membury"),
];

test("a register reads in the order things were entered", () => {
  assert.deepEqual(new Register(LENT).asWritten(), [
    "14 March 1832 | Hannah Skerrett, buried | J. Pring",
    "19 March 1832 | Thomas Vole and Ann Dyke, married | J. Pring",
    "2 April 1832 | Susannah Vole, baptised | R. Membury",
  ]);
});

test("the clerk counts the places from one", () => {
  const register = new Register(LENT);

  assert.equal(register.count(), 3);
  assert.equal(register.at(1)?.what, "Hannah Skerrett, buried");
  assert.equal(register.at(3)?.by, "R. Membury");
  assert.equal(register.at(4), NOTHING_THERE);
  assert.equal(register.at(0), NOTHING_THERE);
});

test("entering something gives back a new register and leaves the old one", () => {
  const register = new Register(LENT);
  const after = register.entered(new Entry("5 April 1832", "John Kellow, buried", "R. Membury"));

  assert.equal(after.count(), 4);
  assert.equal(register.count(), 3);
});

test("a register holding nothing holds nothing", () => {
  assert.deepEqual(new Register().entries(), []);
  assert.equal(new Register().count(), 0);
});
