import test from "node:test";
import assert from "node:assert/strict";

import { Entry, written } from "./entries.ts";

const BURIAL = new Entry("14 March 1832", "Hannah Skerrett, buried", "J. Pring");

test("an entry reads as one line, in the one form", () => {
  assert.equal(written(BURIAL), "14 March 1832 | Hannah Skerrett, buried | J. Pring");
});

test("an entry in different words is a different entry", () => {
  const later = BURIAL.saying("Hannah Skerrett, removed to Bath");

  assert.notEqual(written(later), written(BURIAL));
  assert.equal(later.on, BURIAL.on);
  assert.equal(later.by, BURIAL.by);
  assert.equal(BURIAL.what, "Hannah Skerrett, buried");
});
