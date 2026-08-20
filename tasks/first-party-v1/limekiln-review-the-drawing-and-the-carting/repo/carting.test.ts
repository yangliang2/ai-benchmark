import test from "node:test";
import assert from "node:assert/strict";

import { Load, Sheet } from "./carting.ts";

function madeUp(): Sheet {
  return new Sheet()
    .loaded(new Load("5", 30, 2))
    .loaded(new Load("12", 45, 3))
    .loaded(new Load("5", 20, 7));
}

test("a load is set down on the sheet as it was loaded", () => {
  const [first] = madeUp().loads();

  assert.equal(first.cart, "5");
  assert.equal(first.bushels, 30);
  assert.equal(first.hour, 2);
  assert.deepEqual(
    madeUp().loads().map((load) => load.hour),
    [2, 3, 7],
  );
});

test("what a cart carried away is what went on it", () => {
  assert.equal(madeUp().carried("5"), 50);
  assert.equal(madeUp().carried("12"), 45);
});

test("a cart that never loaded carried none", () => {
  assert.equal(madeUp().carried("9"), 0);
  assert.equal(new Sheet().carried("5"), 0);
});

test("setting a load down leaves the sheet it was set down on alone", () => {
  const sheet = new Sheet();
  const after = sheet.loaded(new Load("5", 30, 2));

  assert.deepEqual(sheet.loads(), []);
  assert.equal(after.loads().length, 1);
});
