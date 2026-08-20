import test from "node:test";
import assert from "node:assert/strict";

import { NOT_A_READING, Reading, line, readLine, readOff, written } from "./readings.ts";

const RETORT_HOUSE = new Reading("retort-house", "1974-03-01", 3120);
const PURIFIERS = new Reading("purifiers", "1974-03-01", 480);

test("a reading is written on one line", () => {
  assert.equal(line(RETORT_HOUSE), "retort-house 1974-03-01 3120");
});

test("a day's readings go on one sheet, one to a line", () => {
  assert.equal(
    written([RETORT_HOUSE, PURIFIERS]),
    "retort-house 1974-03-01 3120\npurifiers 1974-03-01 480\n",
  );
});

test("a sheet with nothing on it is a sheet with nothing on it", () => {
  assert.equal(written([]), "");
  assert.deepEqual(readOff(""), []);
});

test("what was written on a sheet reads back off it, in the order taken", () => {
  assert.deepEqual(readOff(written([RETORT_HOUSE, PURIFIERS])), [RETORT_HOUSE, PURIFIERS]);
});

test("a line nobody can read is not a reading", () => {
  assert.equal(readLine(""), NOT_A_READING);
  assert.equal(readLine("retort-house 1974-03-01"), NOT_A_READING);
  assert.equal(readLine("retort-house 1st March 3120"), NOT_A_READING);
  assert.equal(readLine("retort-house 1974-03-01 a good deal"), NOT_A_READING);
});

test("a line nobody can read is left off the sheet rather than guessed at", () => {
  const sheet = "retort-house 1974-03-01 3120\nsmudge\npurifiers 1974-03-01 480\n";

  assert.deepEqual(readOff(sheet), [RETORT_HOUSE, PURIFIERS]);
});
