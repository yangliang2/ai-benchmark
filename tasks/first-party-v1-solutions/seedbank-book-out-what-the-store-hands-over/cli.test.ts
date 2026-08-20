import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { DONE, NOT_ASKED, REFUSED, run } from "./cli.ts";
import { Packet } from "./packets.ts";
import { Store } from "./store.ts";

/** A drawer of this test's own making, with two packets in it, thrown away after. */
function atTheCounter(work: (root: string) => void): void {
  const made = mkdtempSync(join(tmpdir(), "seedbank-"));
  try {
    const root = join(made, "drawer");
    const store = new Store(root);
    store.file(new Packet("broadbean", "Aquadulce", 1974, 50));
    store.file(new Packet("leek", "Musselburgh", 1981, 300));
    work(root);
  } finally {
    rmSync(made, { recursive: true, force: true });
  }
}

test("the counter lists what the store holds", () => {
  atTheCounter((root) => {
    assert.deepEqual(run(["list"], root), {
      code: DONE,
      lines: ["broadbean", "leek"],
    });
  });
});

test("the counter shows one packet's card", () => {
  atTheCounter((root) => {
    assert.deepEqual(run(["show", "leek"], root), {
      code: DONE,
      lines: ["name: leek", "variety: Musselburgh", "gathered: 1981", "seeds: 300"],
    });
  });
});

test("the counter refuses a name the store has nothing under", () => {
  atTheCounter((root) => {
    assert.equal(run(["show", "marrow"], root).code, REFUSED);
  });
});

test("the counter says so when it is asked something it does not know", () => {
  atTheCounter((root) => {
    assert.equal(run([], root).code, NOT_ASKED);
    assert.equal(run(["burn", "the", "drawer"], root).code, NOT_ASKED);
    assert.equal(run(["show"], root).code, NOT_ASKED);
  });
});
