/**
 * The roll room: where a day's sheet is pressed into a roll and put away.
 *
 * The room does two jobs at once. It keeps the shelf — one roll to a day,
 * under the day the readings were taken — and it works the press itself,
 * reaching for `node:zlib` on its own account and pressing every sheet the
 * one way there is.
 *
 * What is on the shelf is the only copy: `readingsOn` opens the day's roll
 * back out and reads the sheet off it, and a day nothing was put away under
 * is not a day of no readings.
 */

import { gunzipSync, gzipSync } from "node:zlib";

import { Reading, readOff, written } from "./readings.ts";

/** What the shelf gives back for a day it holds no roll under. */
export const NOT_ROLLED = null;

export class RollRoom {
  readonly shelf: Map<string, Uint8Array>;

  constructor() {
    this.shelf = new Map();
  }

  /** Press one day's readings into a roll and put it on the shelf. */
  putAway(day: string, readings: Reading[]): void {
    this.shelf.set(day, gzipSync(written(readings)));
  }

  /** The roll as it lies on the shelf, pressed, or not rolled where none is. */
  roll(day: string): Uint8Array | null {
    return this.shelf.get(day) ?? NOT_ROLLED;
  }

  /** The readings on one day's roll, or not rolled where the shelf holds none. */
  readingsOn(day: string): Reading[] | null {
    const roll = this.shelf.get(day);
    if (roll === undefined) {
      return NOT_ROLLED;
    }
    return readOff(gunzipSync(roll).toString("utf8"));
  }

  /** Every day the shelf holds a roll under, earliest first. */
  days(): string[] {
    return [...this.shelf.keys()].sort();
  }
}
