/**
 * The roll room: where a day's sheet is put away, and taken back off the shelf.
 *
 * The room keeps the shelf — one roll to a day, under the day the readings
 * were taken — and nothing else. The press is somebody else's: the room is
 * handed one when it is built and works every roll through that and through
 * nothing else, so a caller who wants a different press hands one over rather
 * than editing this file.
 *
 * What is on the shelf is the only copy: `readingsOn` opens the day's roll
 * back out and reads the sheet off it, and a day nothing was put away under
 * is not a day of no readings.
 */

import { pressed, unpressed } from "./press.ts";
import { Reading, readOff, written } from "./readings.ts";

/** What the shelf gives back for a day it holds no roll under. */
export const NOT_ROLLED = null;

/** What the room needs of a press: a sheet down, and a sheet back out. */
export type Press = {
  pressed: (sheet: string) => Uint8Array;
  unpressed: (roll: Uint8Array) => string;
};

/** The press the room works with when nobody hands it one. */
export const THE_PRESS: Press = { pressed, unpressed };

export class RollRoom {
  readonly shelf: Map<string, Uint8Array>;
  readonly press: Press;

  constructor(press: Press = THE_PRESS) {
    this.shelf = new Map();
    this.press = press;
  }

  /** Press one day's readings into a roll and put it on the shelf. */
  putAway(day: string, readings: Reading[]): void {
    this.shelf.set(day, this.press.pressed(written(readings)));
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
    return readOff(this.press.unpressed(roll));
  }

  /** Every day the shelf holds a roll under, earliest first. */
  days(): string[] {
    return [...this.shelf.keys()].sort();
  }
}
