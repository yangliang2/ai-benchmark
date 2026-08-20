import test from "node:test";
import assert from "node:assert/strict";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";

import { A_MESSAGE, A_WORD, Charge, Rate } from "./charges.ts";
import { Wire } from "./messages.ts";

/** What this stage made of these messages. */
async function priced(wires: Wire[], rate: Rate): Promise<Charge[]> {
  const off: Charge[] = [];
  await pipeline(Readable.from(wires), rate, async (source) => {
    for await (const charge of source) {
      off.push(charge as Charge);
    }
  });
  return off;
}

test("a message costs the handing in, and a word on top of it", async () => {
  const [charge] = await priced([new Wire("KENDAL", ["two", "trucks"])], new Rate());

  assert.equal(charge?.pence, A_MESSAGE + 2 * A_WORD);
});

test("a message of nothing but an address costs the handing in alone", async () => {
  const [charge] = await priced([new Wire("WIGAN", [])], new Rate());

  assert.equal(charge?.pence, A_MESSAGE);
});

test("an office charging another rate a word charges it", async () => {
  const [charge] = await priced([new Wire("KENDAL", ["one", "two"])], new Rate(5));

  assert.equal(charge?.pence, A_MESSAGE + 2 * 5);
});

test("the charge says whose hand the message was for", async () => {
  const off = await priced(
    [new Wire("KENDAL", ["one"]), new Wire("WIGAN", ["two"])],
    new Rate(),
  );

  assert.deepEqual(off.map((charge) => charge.to), ["KENDAL", "WIGAN"]);
});

test("a charge is not marked a repeat until something marks it one", () => {
  assert.equal(new Charge("KENDAL", 8).again, false);
  assert.equal(new Charge("KENDAL", 8, true).again, true);
});

test("this stage prices every message it is given and holds none of them", async () => {
  const off = await priced(
    [new Wire("A", ["one"]), new Wire("B", ["two"]), new Wire("C", ["three"])],
    new Rate(),
  );

  assert.equal(off.length, 3);
});
