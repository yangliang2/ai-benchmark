import test from "node:test";
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";

import {
  A_WEIGHING,
  FRAME_BYTES,
  KIND_AT,
  NOTHING_OF_THE_KIND,
  frameOf,
  kindOf,
  weighingIn,
} from "./frames.ts";
import { Weighing } from "./weighings.ts";

const LOAD = new Weighing(4021, "Pargeter", 18400, 7250);

test("a weighing goes on the tape in one frame of the fixed width", () => {
  const frame = frameOf(LOAD);

  assert.equal(frame.length, FRAME_BYTES);
  assert.equal(frame.readUInt8(KIND_AT), A_WEIGHING);
});

test("what went on the tape comes back off it", () => {
  assert.deepEqual(weighingIn(frameOf(LOAD)), LOAD);
});

test("a name too long for the tape comes back as much of it as fits", () => {
  const cut = weighingIn(frameOf(new Weighing(7, "Braddock and Sons", 100, 40)));

  assert.equal(cut?.haulier, "Braddock");
});

test("bytes that are not a frame at all are of no kind", () => {
  assert.equal(kindOf(Buffer.alloc(3)), NOTHING_OF_THE_KIND);
  assert.equal(kindOf(Buffer.alloc(FRAME_BYTES + 1)), NOTHING_OF_THE_KIND);
});

test("a frame of another kind is not a weighing", () => {
  const other = Buffer.from(frameOf(LOAD));
  other.writeUInt8(200, KIND_AT);

  assert.equal(weighingIn(other), NOTHING_OF_THE_KIND);
});
