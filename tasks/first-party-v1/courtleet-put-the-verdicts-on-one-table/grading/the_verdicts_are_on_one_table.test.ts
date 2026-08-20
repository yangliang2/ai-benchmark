/**
 * Held out: the structural half. What says the restructuring happened.
 *
 * Both assertions are about runtime shape and neither is about a type, because
 * nothing type-checks at grade time. The first opens `court.ts` and looks at
 * the table itself — that it is there, that it is a `Map`, that it holds one
 * entry to each verdict the court knows and that each entry is something that
 * can be called.
 *
 * The second is the boundary, and it is the one a chain of `if`s cannot
 * survive however it is arranged: a verdict the court has never heard of is
 * put *on the table at run time*, and the court is then asked to rule on a
 * bylaw carrying it. Only a court that reads the table can say the added
 * entry's words back. It is taken off again in a `finally`, and the court is
 * asked once more, so that what the test leaves behind is what it found.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Bylaw } from "./bylaws.ts";
import { Case } from "./cases.ts";
import { Court, UNKNOWN_VERDICT } from "./court.ts";

const STOW = new Court("stow");
const WILLIAM = new Case("william-mason", { beasts: 12, stint: 8 });
const BANISHED = new Bylaw("affray", "beasts > stint", "banishment", 0);

test("the verdicts the court knows are on one table", async () => {
  const court = await import("./court.ts");

  assert.ok(court.VERDICTS instanceof Map);
  assert.deepEqual([...court.VERDICTS.keys()].sort(), [
    "amercement",
    "distraint",
    "pain",
  ]);
  for (const said of court.VERDICTS.values()) {
    assert.equal(typeof said, "function");
  }
});

test("the court rules off that table and not off a chain of its own", async () => {
  const court = await import("./court.ts");
  assert.equal(STOW.rule(BANISHED, WILLIAM).said, UNKNOWN_VERDICT);

  court.VERDICTS.set("banishment", (bylaw) => ({
    bylaw: bylaw.name,
    said: "put out of the manor",
    pence: 0,
  }));
  try {
    assert.deepEqual(STOW.rule(BANISHED, WILLIAM), {
      bylaw: "affray",
      said: "put out of the manor",
      pence: 0,
    });
  } finally {
    court.VERDICTS.delete("banishment");
  }

  assert.equal(STOW.rule(BANISHED, WILLIAM).said, UNKNOWN_VERDICT);
});
