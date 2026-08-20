/**
 * The existence proof of the planted finding ('inscription.ts', 'asCut').
 *
 * Read by the task-set lint and by nothing else: it fails on `repo/`, which
 * ships the change under review already applied, and passes on `corrected/`.
 *
 * The house rule is that every `&` an inscription was given is cut in full as
 * `and`, and every one of them is. The change replaces with a string pattern,
 * which in Node writes out the first occurrence and no other, so an inscription
 * naming two people and their infant goes to the chisel with an ampersand still
 * standing in it.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { asCut } from "./inscription.ts";

test("every ampersand the words were given is cut in full", () => {
  assert.equal(
    asCut("THOMAS VOLE & ANN HIS WIFE & INFANT"),
    "THOMAS VOLE and ANN HIS WIFE and INFANT",
  );
});
