import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { Packet } from "./packets.ts";
import { NOT_IN_THE_STORE, Store } from "./store.ts";

/**
 * A drawer of this test's own making, thrown away after it. Nothing here
 * writes anywhere but a directory it made itself, so two runs of these tests
 * never meet over one path.
 */
function inADrawerOfItsOwn(work: (store: Store) => void): void {
  const root = mkdtempSync(join(tmpdir(), "seedbank-"));
  try {
    work(new Store(join(root, "drawer")));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

test("a packet filed away comes back off its card", () => {
  inADrawerOfItsOwn((store) => {
    const packet = new Packet("broadbean", "Aquadulce", 1974, 50);
    store.file(packet);

    assert.deepEqual(store.packetFor("broadbean"), packet);
  });
});

test("the drawer is made where nobody has made it yet", () => {
  inADrawerOfItsOwn((store) => {
    assert.deepEqual(store.names(), []);
    store.file(new Packet("leek", "Musselburgh", 1981, 300));

    assert.deepEqual(store.names(), ["leek"]);
  });
});

test("the drawer keeps its names in the order they read in", () => {
  inADrawerOfItsOwn((store) => {
    store.file(new Packet("leek", "Musselburgh", 1981, 300));
    store.file(new Packet("broadbean", "Aquadulce", 1974, 50));
    store.file(new Packet("parsnip", "Tender and True", 1968, 120));

    assert.deepEqual(store.names(), ["broadbean", "leek", "parsnip"]);
  });
});

test("a name the drawer holds nothing under is not in the store", () => {
  inADrawerOfItsOwn((store) => {
    assert.equal(store.packetFor("marrow"), NOT_IN_THE_STORE);
  });
});

test("filing a packet again writes over what was there", () => {
  inADrawerOfItsOwn((store) => {
    const packet = new Packet("broadbean", "Aquadulce", 1974, 50);
    store.file(packet);
    store.file(packet.holding(20));

    assert.equal(store.packetFor("broadbean")?.seeds, 20);
    assert.deepEqual(store.names(), ["broadbean"]);
  });
});
