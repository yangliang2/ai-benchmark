import test from "node:test";
import assert from "node:assert/strict";

import { AMPERSAND, IN_FULL, dateOn, lettersIn } from "./inscription.ts";

test("the head of a stone carries the first of the dates it was given", () => {
  assert.equal(dateOn("HANNAH SKERRETT 1832"), "1832");
  assert.equal(dateOn("THOMAS VOLE 1801 1874 HIS WIFE ANN 1878"), "1801");
  assert.equal(dateOn("SACRED TO THE MEMORY OF"), null);
});

test("the letters and figures of what was given are what there is to cut", () => {
  assert.equal(lettersIn("HANNAH SKERRETT 1832"), 18);
  assert.equal(lettersIn("  "), 0);
});

test("the yard knows what it will not cut and what it puts there instead", () => {
  assert.equal(AMPERSAND, "&");
  assert.equal(IN_FULL, "and");
});
