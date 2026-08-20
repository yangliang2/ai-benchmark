import test from "node:test";
import assert from "node:assert/strict";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";

import { Charge } from "./charges.ts";
import { AS_BEFORE, Repeats, Sheet, Totting, footed, writtenUp } from "./sheet.ts";

/** What a stage of the office made of these charges. */
async function through<T>(charges: Charge[], stage: Repeats | Totting): Promise<T[]> {
  const off: T[] = [];
  await pipeline(Readable.from(charges), stage, async (source) => {
    for await (const given of source) {
      off.push(given as T);
    }
  });
  return off;
}

test("a message is written up as whose it was and what it came to", () => {
  assert.equal(writtenUp(new Charge("KENDAL", 18)), "KENDAL: 18d");
});

test("a repeat says so on its own line", () => {
  assert.equal(
    writtenUp(new Charge("KENDAL", 16, true)),
    `KENDAL (${AS_BEFORE}): 16d`,
  );
});

test("the foot says what the sheet holds and what the day came to", () => {
  assert.equal(footed(4, 62), "4 messages, 62d");
});

test("a second message to the same hand is marked a repeat", async () => {
  const off = await through<Charge>(
    [new Charge("KENDAL", 18), new Charge("KENDAL", 16)],
    new Repeats(),
  );

  assert.deepEqual(off.map((charge) => charge.again), [false, true]);
});

test("two messages to different hands are neither of them repeats", async () => {
  const off = await through<Charge>(
    [new Charge("KENDAL", 18), new Charge("WIGAN", 16), new Charge("KENDAL", 12)],
    new Repeats(),
  );

  assert.deepEqual(off.map((charge) => charge.again), [false, false, false]);
});

test("the page is footed when the last message has gone by", async () => {
  const off = await through<string>(
    [new Charge("KENDAL", 18), new Charge("WIGAN", 16)],
    new Totting(),
  );

  assert.deepEqual(off, ["KENDAL: 18d", "WIGAN: 16d", footed(2, 34)]);
});

test("a day nobody sent anything on is footed all the same", async () => {
  assert.deepEqual(await through<string>([], new Totting()), [footed(0, 0)]);
});

test("the sheet keeps its lines in the order they were written", async () => {
  const sheet = new Sheet();

  await pipeline(Readable.from(["one", "two", "three"]), sheet);

  assert.deepEqual(sheet.read(), ["one", "two", "three"]);
});

test("a fresh sheet has nothing on it", () => {
  assert.deepEqual(new Sheet().read(), []);
});
