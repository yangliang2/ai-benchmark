import test from "node:test";
import assert from "node:assert/strict";

import { Reading, written } from "./readings.ts";
import { NOT_ROLLED, RollRoom } from "./rollroom.ts";

const FIRST = [
  new Reading("retort-house", "1974-03-01", 3120),
  new Reading("purifiers", "1974-03-01", 480),
];
const SECOND = [new Reading("retort-house", "1974-03-02", 2980)];

test("a day put away comes back off its roll", () => {
  const room = new RollRoom();
  room.putAway("1974-03-01", FIRST);

  assert.deepEqual(room.readingsOn("1974-03-01"), FIRST);
});

test("what is on the shelf is pressed, and smaller than the sheet that went in", () => {
  const room = new RollRoom();
  const day = Array.from({ length: 20 }, () => FIRST[0]);
  room.putAway("1974-03-01", day);
  const roll = room.roll("1974-03-01");

  assert.deepEqual([roll[0], roll[1]], [0x1f, 0x8b]);
  assert.ok(roll.length < written(day).length);
});

test("a day nothing was put away under holds no roll at all", () => {
  const room = new RollRoom();

  assert.equal(room.roll("1974-03-01"), NOT_ROLLED);
  assert.equal(room.readingsOn("1974-03-01"), NOT_ROLLED);
});

test("the shelf keeps one roll to a day, earliest first", () => {
  const room = new RollRoom();
  room.putAway("1974-03-02", SECOND);
  room.putAway("1974-03-01", FIRST);

  assert.deepEqual(room.days(), ["1974-03-01", "1974-03-02"]);
});

test("putting a day away again writes over the roll that was there", () => {
  const room = new RollRoom();
  room.putAway("1974-03-01", FIRST);
  room.putAway("1974-03-01", SECOND);

  assert.deepEqual(room.readingsOn("1974-03-01"), SECOND);
  assert.deepEqual(room.days(), ["1974-03-01"]);
});
