/**
 * Held out: what stands on the day sheet when the tape ran out with a message
 * still on it.
 *
 * The agent never sees this file. It asserts what the office *ends the day
 * with* and not how it gets there: where the last message is given out, and by
 * which stage, is the fix's own business, and any repair that has every
 * message on the tape read off, charged and written up in the order it was
 * sent passes here.
 *
 * Nothing here waits on a length of time, and nothing here is a fact about how
 * fast the machine grading it happens to be. Every verdict is read off a
 * settled promise and a written page: the day hands back a promise that
 * settles when the drum has stopped, every stage has given out everything it
 * had and the sheet has taken the last line — and the sheet is a list in the
 * order it was written. A test that slept and then looked would be a coin toss
 * on the scheduler, and round 1 has already paid for one of those. Every one
 * of them terminates for the same reason: the run the promise belongs to ends
 * when the tape does, and an unended stream would be a grading timeout, which
 * reads as unresolved and says nothing about the agent.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { A_MESSAGE, A_WORD } from "./charges.ts";
import { A_LENGTH, Office } from "./office.ts";
import { Sheet, footed } from "./sheet.ts";
import { Drum, MARK, inLengths } from "./tape.ts";

/** A day at the office, with the tape cut into the lengths it comes off in. */
function aDay(tape: string, size: number = A_LENGTH): { office: Office; drum: Drum } {
  const drum = new Drum(inLengths(tape, size));
  return { office: new Office(drum, new Sheet()), drum };
}

/** What a message of this many words costs at the standard rate. */
function costing(words: number): number {
  return A_MESSAGE + A_WORD * words;
}

// Tuesday's tape: four messages, and the drum stopped where the fourth ended,
// because nothing was sent after it.
const TUESDAY = [
  `KENDAL two trucks of slate${MARK}`,
  `KENDAL and a wagon of lime${MARK}`,
  `WIGAN the up train is held${MARK}`,
  "CARLISLE nothing more tonight",
].join("");

const THE_DAY = [
  `KENDAL: ${costing(4)}d`,
  `KENDAL (as before): ${costing(5)}d`,
  `WIGAN: ${costing(5)}d`,
  `CARLISLE: ${costing(3)}d`,
  footed(4, costing(4) + costing(5) + costing(5) + costing(3)),
];

test("every message on the tape is on the sheet, in the order it was sent", async () => {
  const { office } = aDay(TUESDAY);

  assert.deepEqual(await office.work(), THE_DAY);
});

test("the last message of the day is charged and counted like any other", async () => {
  const { office } = aDay(TUESDAY);

  const page = await office.work();

  assert.equal(page.at(-2), `CARLISLE: ${costing(3)}d`);
  assert.equal(page.at(-1), footed(4, 58));
});

test("a message that ran across two lengths and ended the tape is one message", async () => {
  const { office } = aDay(`WIGAN the up train${MARK}CARLISLE nothing more`, 9);

  assert.deepEqual(await office.work(), [
    `WIGAN: ${costing(3)}d`,
    `CARLISLE: ${costing(2)}d`,
    footed(2, costing(3) + costing(2)),
  ]);
});

test("a message with nothing after it is the only thing left on the tape", async () => {
  const { office } = aDay(`KENDAL one${MARK}KENDAL two`);

  assert.deepEqual(await office.work(), [
    `KENDAL: ${costing(1)}d`,
    `KENDAL (as before): ${costing(1)}d`,
    footed(2, 2 * costing(1)),
  ]);
});

test("a tape that ends at a mark reads exactly as it did before", async () => {
  const { office } = aDay(`WIGAN the up train is held${MARK}`);

  assert.deepEqual(await office.work(), [
    `WIGAN: ${costing(5)}d`,
    footed(1, costing(5)),
  ]);
});

test("a day nothing was sent on is a page with nothing but its foot", async () => {
  const { office } = aDay("");

  assert.deepEqual(await office.work(), [footed(0, 0)]);
});

test("the whole tape was worked, and the page handed back is the page written", async () => {
  const { office, drum } = aDay(TUESDAY);

  const page = await office.work();

  assert.deepEqual(page, office.sheet.read());
  assert.equal(drum.given(), inLengths(TUESDAY, A_LENGTH).length);
});
