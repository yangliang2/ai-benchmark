import test from "node:test";
import assert from "node:assert/strict";

import { NOT_A_PACKET, Packet, readOff, written } from "./packets.ts";

const BROAD_BEAN = new Packet("broadbean", "Aquadulce", 1974, 50);

test("a packet is written out a field to a line", () => {
  assert.equal(
    written(BROAD_BEAN),
    "name: broadbean\nvariety: Aquadulce\ngathered: 1974\nseeds: 50\n",
  );
});

test("what was written on a card reads back off it", () => {
  const read = readOff(written(BROAD_BEAN));

  assert.deepEqual(read, BROAD_BEAN);
});

test("a card nobody can read is not a packet", () => {
  assert.equal(readOff(""), NOT_A_PACKET);
  assert.equal(readOff("name: broadbean\n"), NOT_A_PACKET);
  assert.equal(readOff("name: broadbean\nvariety: Aquadulce\nseeds: half\n"), NOT_A_PACKET);
});

test("the same packet with fewer seeds in it is the same packet", () => {
  const fewer = BROAD_BEAN.holding(20);

  assert.equal(fewer.seeds, 20);
  assert.equal(fewer.name, "broadbean");
  assert.equal(fewer.variety, "Aquadulce");
  assert.equal(fewer.gathered, 1974);
  assert.equal(BROAD_BEAN.seeds, 50);
});
