/**
 * The existence proof of the planted finding ('dockets.ts', 'Docket.asFigure').
 *
 * Read by the task-set lint and by nothing else: it fails on `repo/`, which
 * ships the change under review already applied, and passes on `corrected/`.
 *
 * The house rule is that a docket says what was drawn as a plain figure of
 * bushels and nothing else, and that anything else written in that place is
 * no figure at all. The change reads the figure with `parseInt`, which takes
 * the figures a docket begins with and passes over whatever the burner wrote
 * after them, so a docket that should have been set aside is drawn on.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Docket } from "./dockets.ts";

test("a docket that does not carry a plain figure is set aside", () => {
  assert.equal(new Docket("TOP", "Trewin", "40 odd", 3).asFigure(), null);
  assert.equal(new Docket("mid", "Penhale", "12 or so", 5).asFigure(), null);
  assert.equal(new Docket("Low", "Roskilly", "25", 9).asFigure(), 25);
});
