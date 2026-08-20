/**
 * Held out: the structural half. What says the restructuring happened.
 *
 * Both assertions are about runtime shape and neither is about a type, because
 * nothing type-checks at grade time: the first opens `press.ts` for real and
 * works the press it exports, and the second builds a roll room around a press
 * of this file's own making and watches the room call it. That second one is
 * the boundary itself — a room that still reaches for `node:zlib` on its own
 * account cannot be made to press a sheet the way this stub presses it,
 * however the file is arranged.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Reading, written } from "./readings.ts";
import { RollRoom } from "./rollroom.ts";

const A_DAY = [
  new Reading("retort-house", "1867-11-04", 3120),
  new Reading("purifiers", "1867-11-04", 480),
];

/** A press of this test's own: it presses nothing and says what it was asked. */
function aPressOfItsOwn(): {
  worked: string[];
  pressed: (sheet: string) => Uint8Array;
  unpressed: (roll: Uint8Array) => string;
} {
  const worked: string[] = [];
  return {
    worked,
    pressed(sheet: string): Uint8Array {
      worked.push("pressed");
      return new TextEncoder().encode(`by hand:${sheet}`);
    },
    unpressed(roll: Uint8Array): string {
      worked.push("unpressed");
      return new TextDecoder().decode(roll).slice("by hand:".length);
    },
  };
}

test("the press stands on its own, in a module of its own", async () => {
  const press = await import("./press.ts");
  const sheet = written(A_DAY);
  const roll = press.pressed(sheet);

  assert.equal(press.unpressed(roll), sheet);
  // The same press it always was, moved rather than replaced.
  assert.deepEqual([roll[0], roll[1]], [0x1f, 0x8b]);
  assert.ok(roll.length > 0);
});

test("the roll room works the press it is handed and no other", () => {
  const press = aPressOfItsOwn();
  const room = new RollRoom(press);
  room.putAway("1867-11-04", A_DAY);

  assert.deepEqual(
    room.roll("1867-11-04"),
    new TextEncoder().encode(`by hand:${written(A_DAY)}`),
  );
  assert.deepEqual(room.readingsOn("1867-11-04"), A_DAY);
  assert.deepEqual(press.worked, ["pressed", "unpressed"]);
});

test("a roll room built with nobody handed over presses all the same", () => {
  const room = new RollRoom();
  room.putAway("1867-11-04", A_DAY);
  const roll = room.roll("1867-11-04");

  assert.deepEqual([roll[0], roll[1]], [0x1f, 0x8b]);
  assert.deepEqual(room.readingsOn("1867-11-04"), A_DAY);
});
