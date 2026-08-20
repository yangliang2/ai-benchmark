/**
 * Held out: what the store hands over, and what it writes down when it does.
 *
 * The agent never sees this file. Every path it touches is under a directory
 * this file made itself and throws away after, so grading writes nowhere but
 * its own workdir and no two tests here ever meet over one path.
 *
 * It asserts what the counter and the drawer *do* and not how they do it: the
 * day book is read back through the module the task asks for, and the cards
 * through the store, so a solution is free to write either however it likes.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { DONE, REFUSED, run } from "./cli.ts";
import { DAYBOOK, handedOut, noted } from "./handouts.ts";
import { Packet } from "./packets.ts";
import { Store } from "./store.ts";

/** A drawer of this test's own making, with two packets in it, thrown away after. */
function inADrawerOfItsOwn(work: (store: Store) => void): void {
  const made = mkdtempSync(join(tmpdir(), "seedbank-grading-"));
  try {
    const store = new Store(join(made, "drawer"));
    store.file(new Packet("broadbean", "Aquadulce", 1974, 50));
    store.file(new Packet("leek", "Musselburgh", 1981, 300));
    work(store);
  } finally {
    rmSync(made, { recursive: true, force: true });
  }
}

/** The day book as it stands, and nothing at all where none has been opened. */
function daybook(store: Store): string[] {
  const kept = join(store.root, DAYBOOK);
  return existsSync(kept) ? handedOut(readFileSync(kept, "utf8")) : [];
}

test("seed handed out comes off the packet and off its card", () => {
  inADrawerOfItsOwn((store) => {
    const left = store.handOut("broadbean", 20);

    assert.equal(left.seeds, 30);
    assert.deepEqual(store.packetFor("broadbean"), new Packet("broadbean", "Aquadulce", 1974, 30));
    assert.deepEqual(store.names(), ["broadbean", "leek"]);
  });
});

test("what went out is written in the day book, in the order it went", () => {
  inADrawerOfItsOwn((store) => {
    store.handOut("broadbean", 20);
    store.handOut("leek", 100);
    store.handOut("broadbean", 30);

    assert.deepEqual(daybook(store), [
      noted("broadbean", 20, 30),
      noted("leek", 100, 200),
      noted("broadbean", 30, 0),
    ]);
  });
});

test("the store refuses more seed than a packet holds, and writes nothing", () => {
  inADrawerOfItsOwn((store) => {
    assert.throws(() => store.handOut("broadbean", 51));

    assert.equal(store.packetFor("broadbean")?.seeds, 50);
    assert.deepEqual(daybook(store), []);
  });
});

test("the store refuses anything that is not a whole number of seeds", () => {
  inADrawerOfItsOwn((store) => {
    for (const asked of [0, -1, 2.5, Number.NaN]) {
      assert.throws(() => store.handOut("leek", asked));
    }

    assert.equal(store.packetFor("leek")?.seeds, 300);
    assert.deepEqual(daybook(store), []);
  });
});

test("the store refuses a name it holds nothing under", () => {
  inADrawerOfItsOwn((store) => {
    assert.throws(() => store.handOut("marrow", 1));

    assert.deepEqual(store.names(), ["broadbean", "leek"]);
    assert.deepEqual(daybook(store), []);
  });
});

test("the counter hands seed over and says exactly what it wrote down", () => {
  inADrawerOfItsOwn((store) => {
    assert.deepEqual(run(["hand-out", "leek", "100"], store.root), {
      code: DONE,
      lines: [noted("leek", 100, 200)],
    });
    assert.equal(store.packetFor("leek")?.seeds, 200);
    assert.deepEqual(daybook(store), [noted("leek", 100, 200)]);
  });
});

test("the counter refuses and leaves the drawer exactly as it was", () => {
  inADrawerOfItsOwn((store) => {
    for (const asked of ["1000", "0", "lots"]) {
      const said = run(["hand-out", "leek", asked], store.root);

      assert.equal(said.code, REFUSED);
      assert.equal(said.lines.length, 1);
    }
    assert.equal(run(["hand-out", "marrow", "1"], store.root).code, REFUSED);

    assert.equal(store.packetFor("leek")?.seeds, 300);
    assert.deepEqual(daybook(store), []);
  });
});

test("what the counter could already do it does exactly as before", () => {
  inADrawerOfItsOwn((store) => {
    store.handOut("leek", 100);

    assert.deepEqual(run(["list"], store.root), {
      code: DONE,
      lines: ["broadbean", "leek"],
    });
    assert.deepEqual(run(["show", "leek"], store.root), {
      code: DONE,
      lines: ["name: leek", "variety: Musselburgh", "gathered: 1981", "seeds: 200"],
    });
  });
});
