/**
 * The existence proof of the planted finding ('carting.ts', 'Sheet.carts').
 *
 * Read by the task-set lint and by nothing else: it fails on `repo/`, which
 * ships the change under review already applied, and passes on `corrected/`.
 *
 * The house rule is that the sheet names every cart that carried away in the
 * order it first loaded. The change reads the carts off the keys of an object
 * it put them into, and a key that reads as a whole number comes back in
 * counting order and not in the order it was put there, so a day the carts
 * came in any other order is written up in the wrong one.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Load, Sheet } from "./carting.ts";

test("the sheet names the carts in the order each of them first loaded", () => {
  const sheet = new Sheet()
    .loaded(new Load("5", 30, 2))
    .loaded(new Load("12", 45, 3))
    .loaded(new Load("3", 25, 5))
    .loaded(new Load("5", 20, 7));

  assert.deepEqual(sheet.carts(), ["5", "12", "3"]);
});
