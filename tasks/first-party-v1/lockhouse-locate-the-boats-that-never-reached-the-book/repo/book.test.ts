import test from "node:test";
import assert from "node:assert/strict";

import {
  Book,
  HEADING,
  markedAt,
  NOT_GAUGED_UP,
  turnedBack,
  writtenUp,
} from "./book.ts";
import { Boat, Cut, WATER } from "./water.ts";

test("the page reads back in the order it was written", () => {
  const book = new Book();

  book.write("Sally: 8, 28 minutes");
  book.write("Kingfisher: 6, 22 minutes");

  assert.deepEqual(book.read(), [
    "Sally: 8, 28 minutes",
    "Kingfisher: 6, 22 minutes",
  ]);
});

test("a boat is written up with what it sat at and how long it took", () => {
  assert.equal(writtenUp(new Boat("Sally", 20, 8), 28), "Sally: 8, 28 minutes");
});

test("a boat nobody gauged is written up as not gauged", () => {
  assert.equal(
    writtenUp(new Boat("Emily Jane", 18), 26),
    `Emily Jane: ${NOT_GAUGED_UP}, 26 minutes`,
  );
});

test("a boat the orders will not take is written up as turned back", () => {
  assert.equal(turnedBack(new Boat("Bittern", 30, 12)), "Bittern: turned back");
});

test("the page is headed by the first boat up and by none of the ones behind it", () => {
  const cut = new Cut();
  const book = new Book();
  book.headed(cut);

  cut.aBoat(new Boat("Sally", 20, 8));
  cut.aBoat(new Boat("Kingfisher", 14, 6));
  cut.aBoat(new Boat("Bittern", 30, 12));

  assert.deepEqual(book.read(), [HEADING]);
});

test("the mark is noted off the first drawing of the night and no later one", async () => {
  const cut = new Cut();
  const book = new Book();
  book.marked(cut);
  const drawn = new Promise<void>((twice) => {
    let seen = 0;
    cut.on(WATER, () => {
      seen += 1;
      if (seen === 2) {
        twice();
      }
    });
  });

  cut.drawing(30);
  cut.drawing(29);
  await drawn;

  assert.deepEqual(book.read(), [markedAt(30)]);
});
