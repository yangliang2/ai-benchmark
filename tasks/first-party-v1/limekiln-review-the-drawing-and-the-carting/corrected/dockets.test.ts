import test from "node:test";
import assert from "node:assert/strict";

import { DayBook, Docket } from "./dockets.ts";

function handedIn(): DayBook {
  const book = new DayBook();
  book.take(new Docket("TOP", "Trewin", "40", 1));
  book.take(new Docket("mid", "Roskilly", "a few", 4));
  book.take(new Docket("TOP", "Trewin", "25", 6));
  return book;
}

test("the book holds the dockets in the order they came", () => {
  assert.deepEqual(
    handedIn().dockets().map((docket) => docket.hour),
    [1, 4, 6],
  );
  assert.equal(handedIn().count(), 3);
});

test("a docket is set down as it was handed in", () => {
  const [first] = handedIn().dockets();

  assert.equal(first.mark, "TOP");
  assert.equal(first.who, "Trewin");
  assert.equal(first.written, "40");
});

test("the dockets one burner drew come back in the order they came", () => {
  assert.deepEqual(
    handedIn().forBurner("Trewin").map((docket) => docket.hour),
    [1, 6],
  );
  assert.deepEqual(handedIn().forBurner("Penhale"), []);
});

test("what the day drew leaves the dockets that were set aside out of it", () => {
  assert.equal(handedIn().drawn(), 65);
  assert.equal(new DayBook().drawn(), 0);
});
