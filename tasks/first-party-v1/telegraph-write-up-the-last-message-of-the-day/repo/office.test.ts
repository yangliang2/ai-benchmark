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

const TUESDAY = [
  `KENDAL two trucks of slate${MARK}`,
  `KENDAL and a wagon of lime${MARK}`,
  `WIGAN the up train is held${MARK}`,
].join("");

test("a day's tape is written up a line a message, in the order it was sent", async () => {
  const { office } = aDay(TUESDAY);

  assert.deepEqual(await office.work(), [
    `KENDAL: ${costing(4)}d`,
    `KENDAL (as before): ${costing(5)}d`,
    `WIGAN: ${costing(5)}d`,
    footed(3, costing(4) + costing(5) + costing(5)),
  ]);
});

test("the foot counts the lines the sheet holds", async () => {
  const { office } = aDay(TUESDAY);

  const page = await office.work();

  assert.equal(page.at(-1), footed(page.length - 1, costing(4) + 2 * costing(5)));
});

test("the sheet the office hands back is the sheet it wrote", async () => {
  const { office } = aDay(TUESDAY);

  assert.deepEqual(await office.work(), office.sheet.read());
});

test("no tape is given out until the day is worked, and then all of it is", async () => {
  const { office, drum } = aDay(TUESDAY);

  assert.equal(drum.given(), 0);
  await office.work();

  assert.equal(drum.given(), inLengths(TUESDAY, A_LENGTH).length);
});

test("a message spread over two lengths of tape is one line on the sheet", async () => {
  const { office } = aDay(`KENDAL two trucks of slate${MARK}`, 8);

  assert.deepEqual(await office.work(), [
    `KENDAL: ${costing(4)}d`,
    footed(1, costing(4)),
  ]);
});

test("a day nothing was sent on is a page with nothing but its foot", async () => {
  const { office } = aDay("");

  assert.deepEqual(await office.work(), [footed(0, 0)]);
});

test("an office charging another rate a word writes that up", async () => {
  const drum = new Drum(inLengths(`WIGAN the up train is held${MARK}`, A_LENGTH));

  const page = await new Office(drum, new Sheet(), 5).work();

  assert.deepEqual(page, [`WIGAN: ${A_MESSAGE + 5 * 5}d`, footed(1, A_MESSAGE + 25)]);
});
