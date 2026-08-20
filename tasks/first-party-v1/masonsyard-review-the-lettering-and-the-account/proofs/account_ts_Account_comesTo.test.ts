/**
 * The existence proof of the planted finding ('account.ts', 'Account.comesTo').
 *
 * Read by the task-set lint and by nothing else: it fails on `repo/`, which
 * ships the change under review already applied, and passes on `corrected/`.
 *
 * The house rule is that a line of an account is worked out in pence and kept
 * in pence, and only the foot is brought to whole shillings. The change brings
 * every line to shillings on its way past, so two small pieces that come to a
 * shilling and more between them come to nothing at all at the foot.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Account, Piece, Rate } from "./account.ts";
import { Stone } from "./stones.ts";

test("the odd pence are dropped at the foot and nowhere before it", () => {
  const rate = new Rate(7, 30);
  const account = new Account(rate)
    .setDown(new Piece(new Stone("A1", "slate", 1), "HANNAH SKERRETT 1832"))
    .setDown(new Piece(new Stone("b2", "limestone", 1), "JOHN SKERRETT 1836"));

  assert.deepEqual(account.lines(), [7, 7]);
  assert.equal(account.comesTo(), 1);
});
