/**
 * Held out: the structural half. What says the restructuring happened.
 *
 * Every assertion is about runtime shape and none is about a type, because
 * nothing type-checks at grade time. The first opens `links.ts` for real and
 * works what it exports. The second is the load-bearing one: it looks at a
 * ticket as it stands at run time and finds no writing on it at all — no
 * `asLink` anywhere up its prototype chain, no `readLink` on the class — which
 * is what a `typeof` on a declaration could never say. Together they are the
 * boundary: the gate goes on writing exactly the link it wrote before, and the
 * only thing left in the repository that can write one is `links.ts`.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Gate } from "./gate.ts";
import { Ticket } from "./tickets.ts";

const A_WAGGON = new Ticket("westgate", "waggon", 4, true);
const WRITTEN = "toll://westgate/pass?traffic=waggon&axles=4&laden=yes";

test("the writing and the reading of a pass stand on their own", async () => {
  const links = await import("./links.ts");

  assert.equal(links.linkFor(A_WAGGON), WRITTEN);
  assert.deepEqual(links.ticketFrom(WRITTEN), A_WAGGON);
  assert.deepEqual(links.ticketFrom(links.linkFor(A_WAGGON)), A_WAGGON);
  assert.equal(links.ticketFrom("a scrap of paper"), null);
});

test("a ticket does nothing now but say what is owed on it", () => {
  assert.equal("asLink" in A_WAGGON, false);
  assert.equal("readLink" in Ticket, false);
  assert.equal(typeof A_WAGGON.owed, "function");
  assert.equal(A_WAGGON.owed(), 26);
});

test("the gate writes and reads through that module and through nothing else", async () => {
  const links = await import("./links.ts");
  const gate = new Gate("westgate");
  const cart = new Ticket("westgate", "cart", 2, false);

  assert.equal(gate.write(cart), links.linkFor(cart));
  assert.deepEqual(gate.readBack(links.linkFor(cart)), cart);
  assert.equal(gate.charge(links.linkFor(cart)), 8);
});
