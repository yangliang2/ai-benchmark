import test from "node:test";
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";

import { FRAME_BYTES } from "./frames.ts";
import { NOT_ON_THE_TAPE, Tape } from "./tape.ts";
import { Weighing } from "./weighings.ts";

const MORNING = [
  new Weighing(4021, "Pargeter", 18400, 7250),
  new Weighing(4022, "Kyte", 12000, 6100),
  new Weighing(4023, "Braddock", 30500, 12750),
];

test("a tape of weighings reads back as the weighings that went on it", () => {
  assert.deepEqual(Tape.of(MORNING).weighings(), MORNING);
});

test("a tape is frames end to end, all of one width", () => {
  const frames = Tape.of(MORNING).frames();

  assert.equal(frames.length, 3);
  for (const frame of frames) {
    assert.equal(frame.length, FRAME_BYTES);
  }
});

test("a tail too short to be a frame is read as nothing at all", () => {
  const cut = new Tape(Buffer.concat([Tape.of(MORNING).bytes, Buffer.alloc(5)]));

  assert.equal(cut.frames().length, 3);
  assert.deepEqual(cut.weighings(), MORNING);
});

test("weighing again gives back a new tape and leaves the old one alone", () => {
  const morning = Tape.of(MORNING);
  const afternoon = morning.weighed(new Weighing(4024, "Kyte", 9000, 6100));

  assert.equal(afternoon.weighings().length, 4);
  assert.equal(morning.weighings().length, 3);
});

test("what stands against one ticket comes off the tape", () => {
  const tape = Tape.of(MORNING);

  assert.equal(tape.forTicket(4022)?.netKg(), 5900);
  assert.equal(tape.forTicket(9999), NOT_ON_THE_TAPE);
});
