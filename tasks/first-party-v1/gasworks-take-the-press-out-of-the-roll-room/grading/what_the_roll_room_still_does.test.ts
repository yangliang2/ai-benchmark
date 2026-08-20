/**
 * Held out: the behaviour half. What the roll room and the office do must not
 * change, whoever works the press — so every line of this file passes on the
 * pristine repository and has to go on passing once the press has been taken
 * out of the room.
 *
 * Everything here goes through a roll room built the way it is built now, with
 * nobody handed over, because that is the surface the restructuring must leave
 * standing: a room built with no press at all still presses, and still presses
 * the one way it presses now.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { NOTHING_TAKEN, Office } from "./office.ts";
import { Reading, readOff, written } from "./readings.ts";
import { NOT_ROLLED, RollRoom } from "./rollroom.ts";

const A_DAY = [
  new Reading("retort-house", "1867-11-04", 3120),
  new Reading("purifiers", "1867-11-04", 480),
  new Reading("governor-house", "1867-11-04", 95),
];

test("a day's readings come back off the shelf as they went on", () => {
  const room = new RollRoom();
  room.putAway("1867-11-04", A_DAY);

  assert.deepEqual(room.readingsOn("1867-11-04"), A_DAY);
});

test("the roll on the shelf is a pressed roll and not the sheet itself", () => {
  const room = new RollRoom();
  const long = Array.from({ length: 40 }, () => A_DAY[0]);
  room.putAway("1867-11-04", long);
  const roll = room.roll("1867-11-04");

  assert.deepEqual([roll[0], roll[1]], [0x1f, 0x8b]);
  assert.ok(roll.length < written(long).length / 4);
});

test("a day nothing was put away under is not a day of no readings", () => {
  const room = new RollRoom();
  room.putAway("1867-11-04", A_DAY);

  assert.equal(room.roll("1867-11-05"), NOT_ROLLED);
  assert.equal(room.readingsOn("1867-11-05"), NOT_ROLLED);
  assert.deepEqual(room.days(), ["1867-11-04"]);
});

test("a day put away with nothing on the sheet is a day of no readings", () => {
  const room = new RollRoom();
  room.putAway("1867-11-04", []);

  assert.deepEqual(room.readingsOn("1867-11-04"), []);
  assert.notEqual(room.roll("1867-11-04"), NOT_ROLLED);
  assert.deepEqual(room.days(), ["1867-11-04"]);
});

test("the shelf keeps its days earliest first, whatever order they came in", () => {
  const room = new RollRoom();
  for (const day of ["1867-11-06", "1867-11-04", "1867-11-05"]) {
    room.putAway(day, A_DAY);
  }

  assert.deepEqual(room.days(), ["1867-11-04", "1867-11-05", "1867-11-06"]);
});

test("the office works its figures off the day's roll", () => {
  const office = new Office(new RollRoom());
  office.takeIn("1867-11-04", A_DAY);

  assert.equal(office.madeOn("1867-11-04"), 3695);
  assert.deepEqual(office.metersOn("1867-11-04"), [
    "retort-house",
    "purifiers",
    "governor-house",
  ]);
  assert.deepEqual(office.days(), ["1867-11-04"]);
});

test("a day the office took nothing in on is nothing taken, and not nought", () => {
  const office = new Office(new RollRoom());

  assert.equal(office.madeOn("1867-11-04"), NOTHING_TAKEN);
  assert.deepEqual(office.metersOn("1867-11-04"), []);
});

test("a sheet still leaves off the lines nobody can read", () => {
  const room = new RollRoom();
  room.putAway("1867-11-04", A_DAY);
  const sheet = written(A_DAY);

  assert.deepEqual(readOff(`${sheet}a blot\n`), A_DAY);
  assert.deepEqual(readOff(sheet), room.readingsOn("1867-11-04"));
});
