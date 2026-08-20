/**
 * Held out: what the tape settles at once a lorry has been weighed twice.
 *
 * The agent never sees this file. It asserts what the tape *reads back* and
 * not how a correction is laid out beyond the two things the yard's other
 * machines depend on — that a frame is one width, and that its first byte says
 * what kind it is. Everything else goes on the tape and comes back off it
 * through the task's own two functions, so a solution is free to put the
 * figures wherever it likes inside the frame.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";

import { A_CORRECTION, Correction, correctionFrame, correctionIn } from "./corrections.ts";
import { A_WEIGHING, FRAME_BYTES, KIND_AT, kindOf, weighingIn } from "./frames.ts";
import { Tape } from "./tape.ts";
import { Weighing } from "./weighings.ts";

const MORNING = [
  new Weighing(4021, "Pargeter", 18400, 7250),
  new Weighing(4022, "Kyte", 12000, 6100),
  new Weighing(4023, "Braddock", 30500, 12750),
];

/** The morning's tape, with 4022 weighed again after the plate was seen to. */
function theMorningThePlateWasOut(): Tape {
  return Tape.of(MORNING).corrected(new Correction(4022, 12600, 6100));
}

test("a correction goes on the tape in one frame of the yard's own width", () => {
  const frame = correctionFrame(new Correction(4022, 12600, 6100));

  assert.equal(frame.length, FRAME_BYTES);
  assert.equal(frame.readUInt8(KIND_AT), A_CORRECTION);
  assert.notEqual(A_CORRECTION, A_WEIGHING);
});

test("what went on the tape as a correction comes back off it", () => {
  const put = new Correction(4022, 12600, 6100);

  assert.deepEqual(correctionIn(correctionFrame(put)), put);
  assert.equal(correctionIn(correctionFrame(put))?.netKg(), 6500);
});

test("a frame of another kind is not a correction, and the other way about", () => {
  const weighing = Tape.of(MORNING).frames()[0];
  const correction = correctionFrame(new Correction(4022, 12600, 6100));

  assert.equal(correctionIn(weighing), null);
  assert.equal(weighingIn(correction), null);
  assert.equal(kindOf(correction), A_CORRECTION);
  assert.equal(correctionIn(Buffer.alloc(3)), null);
});

test("the corrections on a tape come back in the order they were written", () => {
  const tape = theMorningThePlateWasOut().corrected(new Correction(4021, 18900, 7250));

  assert.deepEqual(tape.corrections(), [
    new Correction(4022, 12600, 6100),
    new Correction(4021, 18900, 7250),
  ]);
});

test("the tape settles at the corrected figures, in the order weighed", () => {
  const settled = theMorningThePlateWasOut().settled();

  assert.deepEqual(
    settled.map((weighing) => [weighing.ticket, weighing.netKg()]),
    [
      [4021, 11150],
      [4022, 6500],
      [4023, 17750],
    ],
  );
  assert.equal(settled[1].haulier, "Kyte");
});

test("the last word against one ticket is the one that stands", () => {
  const tape = theMorningThePlateWasOut()
    .corrected(new Correction(4022, 12900, 6100))
    .corrected(new Correction(4022, 12800, 6050));

  assert.equal(tape.netFor(4022), 6750);
});

test("a correction against a ticket nobody weighed corrects nothing", () => {
  const tape = theMorningThePlateWasOut().corrected(new Correction(9999, 1, 0));

  assert.equal(tape.settled().length, 3);
  assert.equal(tape.netFor(9999), null);
});

test("what one lorry finally netted comes off the tape", () => {
  const tape = theMorningThePlateWasOut();

  assert.equal(tape.netFor(4021), 11150);
  assert.equal(tape.netFor(4022), 6500);
  assert.equal(tape.netFor(4023), 17750);
});

test("what the tape already did it does exactly as before", () => {
  const tape = theMorningThePlateWasOut();

  assert.deepEqual(tape.weighings(), MORNING);
  assert.equal(tape.forTicket(4022)?.netKg(), 5900);
  assert.equal(tape.frames().length, 4);
  assert.equal(tape.bytes.length, 4 * FRAME_BYTES);
});
