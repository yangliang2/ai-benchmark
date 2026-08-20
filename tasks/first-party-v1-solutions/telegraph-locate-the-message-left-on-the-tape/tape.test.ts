import test from "node:test";
import assert from "node:assert/strict";

import { Drum, MARK, inLengths } from "./tape.ts";

/** Everything the drum gave out, in the order it gave it out. */
async function offTheDrum(drum: Drum): Promise<string[]> {
  const off: string[] = [];
  for await (const length of drum) {
    off.push(length as string);
  }
  return off;
}

test("a tape is cut into lengths of the size the drum gives out", () => {
  assert.deepEqual(inLengths("abcdefg", 3), ["abc", "def", "g"]);
  assert.deepEqual(inLengths("", 3), []);
});

test("the drum gives out nothing until a length is asked for", () => {
  const drum = new Drum(["one", "two"]);

  assert.equal(drum.given(), 0);
});

test("the drum gives out every length it was given, in the order it came", async () => {
  const drum = new Drum([`A one${MARK}`, `B two${MARK}`, `C three${MARK}`]);

  assert.deepEqual(await offTheDrum(drum), [
    `A one${MARK}`,
    `B two${MARK}`,
    `C three${MARK}`,
  ]);
  assert.equal(drum.given(), 3);
});

test("a drum with no tape on it gives out nothing at all", async () => {
  const drum = new Drum([]);

  assert.deepEqual(await offTheDrum(drum), []);
  assert.equal(drum.given(), 0);
});

test("the mark is one character, and it is what stands between messages", () => {
  assert.equal(MARK.length, 1);
  assert.deepEqual(`A one${MARK}B two${MARK}`.split(MARK), ["A one", "B two", ""]);
});
