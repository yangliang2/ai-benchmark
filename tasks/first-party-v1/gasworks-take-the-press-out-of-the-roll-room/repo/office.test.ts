import test from "node:test";
import assert from "node:assert/strict";

import { NOTHING_TAKEN, Office } from "./office.ts";
import { Reading } from "./readings.ts";
import { RollRoom } from "./rollroom.ts";

const FIRST = [
  new Reading("retort-house", "1974-03-01", 3120),
  new Reading("purifiers", "1974-03-01", 480),
];

/** An office over a roll room of this test's own, with one day taken in. */
function atTheOffice(work: (office: Office) => void): void {
  const office = new Office(new RollRoom());
  office.takeIn("1974-03-01", FIRST);
  work(office);
}

test("the office says what the works made on a day", () => {
  atTheOffice((office) => {
    assert.equal(office.madeOn("1974-03-01"), 3600);
  });
});

test("the office says which meters were read, in the order they were read", () => {
  atTheOffice((office) => {
    assert.deepEqual(office.metersOn("1974-03-01"), ["retort-house", "purifiers"]);
  });
});

test("a day nothing was taken in on is nothing taken, and not nought made", () => {
  atTheOffice((office) => {
    assert.equal(office.madeOn("1974-03-09"), NOTHING_TAKEN);
    assert.deepEqual(office.metersOn("1974-03-09"), []);
  });
});

test("the office has the days the roll room has", () => {
  atTheOffice((office) => {
    office.takeIn("1974-03-02", [new Reading("retort-house", "1974-03-02", 2980)]);

    assert.deepEqual(office.days(), ["1974-03-01", "1974-03-02"]);
  });
});
