/**
 * The wax: how a seal is taken over a text, and what nothing is sealed with.
 *
 * This module knows one thing — how to take a seal over a text — and nothing
 * whatever about registers, entries or the order any of them come in. What is
 * sealed onto what is the register's own business.
 *
 * A seal is written out in hex, always the same width, so two of them can be
 * set beside each other and compared as they stand.
 */

import { createHash } from "node:crypto";

/** How many characters a seal is written in. */
export const SEAL_WIDTH = 64;

/** What stands before the first entry of a register: nothing sealed at all. */
export const THE_FIRST_SEAL = "0".repeat(SEAL_WIDTH);

/** The seal over one text. */
export function sealOf(text: string): string {
  return createHash("sha256").update(text, "utf8").digest("hex");
}
