/**
 * The press: a sheet pressed down into a roll, and a roll opened back out.
 *
 * The one place `node:zlib` is reached for. Nothing here knows what a sheet
 * says or what a roll is put away under — it presses text down and opens it
 * back out, and the roll room does the keeping.
 */

import { gunzipSync, gzipSync } from "node:zlib";

/** The roll a sheet presses down into. */
export function pressed(sheet: string): Uint8Array {
  return gzipSync(sheet);
}

/** The sheet a roll opens back out to. */
export function unpressed(roll: Uint8Array): string {
  return gunzipSync(roll).toString("utf8");
}
