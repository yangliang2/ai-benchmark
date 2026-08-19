import test from "node:test";
import assert from "node:assert/strict";

import { A_BOAT, Boat, Cut, NOT_GAUGED, WATER } from "./water.ts";

test("a boat nobody brought past the gauge board sits at not gauged", () => {
  assert.equal(new Boat("Emily Jane", 18).deep, NOT_GAUGED);
  assert.equal(new Boat("Sally", 20, 8).deep, 8);
});

test("the cut gives out every boat that comes up to the gate", () => {
  const cut = new Cut();
  const came: string[] = [];
  cut.on(A_BOAT, (boat: Boat) => came.push(boat.name));

  cut.aBoat(new Boat("Sally", 20, 8));
  cut.aBoat(new Boat("Kingfisher", 14, 6));
  cut.aBoat(new Boat("Bittern", 30, 12));

  assert.deepEqual(came, ["Sally", "Kingfisher", "Bittern"]);
});

test("the night shuts once, whatever is said after it", () => {
  const cut = new Cut();
  let shut = 0;
  cut.whenShutting(() => {
    shut += 1;
  });

  cut.shutting();
  cut.shutting();

  assert.equal(shut, 1);
});

test("the pound is given out when it has come up, and not before", async () => {
  const cut = new Cut();
  const stood: number[] = [];
  cut.on(WATER, (inches: number) => stood.push(inches));
  const up = new Promise<number>((come) => {
    cut.once(WATER, come);
  });

  cut.drawing(30);
  assert.deepEqual(stood, []);

  assert.equal(await up, 30);
  assert.deepEqual(stood, [30]);
});
