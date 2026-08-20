/**
 * The existence proof of the planted finding ('orders.ts', 'Book.strikeOff').
 *
 * Read by the task-set lint and by nothing else: it fails on `repo/`, which
 * ships the change under review already applied, and passes on `corrected/`.
 *
 * The house rule is that an order struck off is out of the book and the book is
 * the shorter for it. The change takes the order out of its place without
 * closing the place up, so the book still counts what is no longer in it and
 * what is left standing has a hole where the struck order was.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Book, Order } from "./orders.ts";

test("the book is the shorter for an order struck off", () => {
  const book = new Book();
  book.take(new Order("A1", "Skerrett", "HANNAH SKERRETT 1832", 3));
  book.take(new Order("b2", "Vole", "THOMAS VOLE 1834", 5));
  book.take(new Order("C3", "Skerrett", "JOHN SKERRETT 1836", 5));

  book.strikeOff("b2");

  assert.equal(book.count(), 2);
  assert.deepEqual(
    book.orders().map((order) => order.mark),
    ["A1", "C3"],
  );
});
