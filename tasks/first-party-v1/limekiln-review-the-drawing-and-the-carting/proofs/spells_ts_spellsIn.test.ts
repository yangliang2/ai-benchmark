/**
 * The existence proof of the planted finding ('spells.ts', 'spellsIn').
 *
 * Read by the task-set lint and by nothing else: it fails on `repo/`, which
 * ships the change under review already applied, and passes on `corrected/`.
 *
 * The house rule is that the last spell of the day is a spell like any other.
 * The change closes a spell only where the next burner takes the kiln over,
 * so the burner who had it at the end of the day is never written up at all.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Docket } from "./dockets.ts";
import { spellsIn } from "./spells.ts";

test("the burner who had the kiln last is written up like the rest", () => {
  const handedIn = [
    new Docket("TOP", "Trewin", "40", 1),
    new Docket("TOP", "Trewin", "35", 4),
    new Docket("mid", "Roskilly", "50", 7),
    new Docket("mid", "Roskilly", "20", 11),
  ];

  assert.deepEqual(spellsIn(handedIn), [
    { burner: "Trewin", from: 1, to: 4 },
    { burner: "Roskilly", from: 7, to: 11 },
  ]);
});
