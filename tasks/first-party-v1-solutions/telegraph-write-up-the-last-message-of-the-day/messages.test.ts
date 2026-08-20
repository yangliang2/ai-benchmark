import test from "node:test";
import assert from "node:assert/strict";
import { pipeline } from "node:stream/promises";

import { Cutter, UNADDRESSED, Wire, readOff } from "./messages.ts";
import { Drum, MARK } from "./tape.ts";

/** Every message the cutter made of these lengths of tape. */
async function messagesOff(lengths: string[]): Promise<Wire[]> {
  const off: Wire[] = [];
  await pipeline(new Drum(lengths), new Cutter(), async (source) => {
    for await (const wire of source) {
      off.push(wire as Wire);
    }
  });
  return off;
}

/** The two things a message is, as a pair anyone can read in an assertion. */
function asRead(wire: Wire): [string, string[]] {
  return [wire.to, wire.words];
}

test("a message is taken from the tape as its address and then its words", () => {
  const wire = readOff("KENDAL two trucks of slate");

  assert.equal(wire.to, "KENDAL");
  assert.deepEqual(wire.words, ["two", "trucks", "of", "slate"]);
  assert.equal(wire.count(), 4);
});

test("a message that is nothing but an address has no words to pay for", () => {
  assert.equal(readOff("WIGAN").count(), 0);
});

test("a message with nothing on it at all stands as unaddressed", () => {
  assert.equal(readOff("   ").to, UNADDRESSED);
});

test("the cutter gives out a message for every mark on the tape", async () => {
  const off = await messagesOff([`A one two${MARK}B three${MARK}C lime${MARK}`]);

  assert.deepEqual(off.map(asRead), [
    ["A", ["one", "two"]],
    ["B", ["three"]],
    ["C", ["lime"]],
  ]);
});

test("a message spread over two lengths is one message all the same", async () => {
  const off = await messagesOff([`A one two${MARK}B thr`, `ee slate${MARK}`]);

  assert.deepEqual(off.map(asRead), [
    ["A", ["one", "two"]],
    ["B", ["three", "slate"]],
  ]);
});

test("a message spread over three lengths is one message all the same", async () => {
  const off = await messagesOff(["A one ", "two thr", `ee${MARK}`]);

  assert.deepEqual(off.map(asRead), [["A", ["one", "two", "three"]]]);
});

test("nothing between two marks is no message at all", async () => {
  const off = await messagesOff([`A one${MARK}${MARK}B two${MARK}`]);

  assert.deepEqual(off.map(asRead), [["A", ["one"]], ["B", ["two"]]]);
});

test("a tape with nothing on it yields no messages", async () => {
  assert.deepEqual(await messagesOff([]), []);
});
