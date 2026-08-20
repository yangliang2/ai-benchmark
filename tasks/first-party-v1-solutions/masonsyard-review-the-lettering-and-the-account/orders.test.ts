import test from "node:test";
import assert from "node:assert/strict";

import { Book, Order } from "./orders.ts";

function taken(): Book {
  const book = new Book();
  book.take(new Order("A1", "Skerrett", "HANNAH SKERRETT 1832", 3));
  book.take(new Order("b2", "Vole", "THOMAS VOLE & ANN VOLE 1834", 5));
  book.take(new Order("C3", "Skerrett", "JOHN SKERRETT 1836", 5));
  return book;
}

test("the book holds the orders in the order they came", () => {
  assert.deepEqual(
    taken().orders().map((order) => order.mark),
    ["A1", "b2", "C3"],
  );
});

test("an order is set down as it was taken", () => {
  const [first] = taken().orders();

  assert.equal(first.who, "Skerrett");
  assert.equal(first.given, "HANNAH SKERRETT 1832");
  assert.equal(first.week, 3);
});

test("the orders taken for one name come back in the order they came", () => {
  assert.deepEqual(
    taken().forName("Skerrett").map((order) => order.mark),
    ["A1", "C3"],
  );
  assert.deepEqual(taken().forName("Dyke"), []);
});

test("the orders wanted by a week come back in the order they came", () => {
  assert.deepEqual(
    taken().dueBy(5).map((order) => order.mark),
    ["A1", "b2", "C3"],
  );
  assert.deepEqual(
    taken().dueBy(3).map((order) => order.mark),
    ["A1"],
  );
  assert.deepEqual(taken().dueBy(1), []);
});
