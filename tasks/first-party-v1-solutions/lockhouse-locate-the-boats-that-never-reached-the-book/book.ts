/**
 * The book the lockhouse keeps, and how one boat is written up in it.
 *
 * A page a night, and what stands on the page is a sequence: the line for one
 * boat stands where that boat stood in the night, so reading the page back
 * says what happened and in what order. Nothing is ever written into the
 * middle of it.
 *
 * The page is headed by the first boat up, and the mark the pound was drawn
 * to is noted the first time it is drawn. Both of those are hung on the first
 * of the thing they wait for rather than on every one of it, because a page is
 * headed once and the mark is noted once, and a page headed four times over is
 * not a page anybody could read back.
 */

import { A_BOAT, Boat, Cut, WATER } from "./water.ts";

/** What stands where a depth would, for a boat nobody gauged. */
export const NOT_GAUGED_UP = "not gauged";

/** What the page is headed with. */
export const HEADING = "the night's work";

/** What the mark the pound was drawn to is written up as. */
export function markedAt(inches: number): string {
  return `the pound at ${inches}`;
}

export class Book {
  private readonly lines: string[] = [];

  /** Write one line under whatever stands on the page already. */
  write(line: string): void {
    this.lines.push(line);
  }

  /** The page as it stands: every line of it, in the order it was written. */
  read(): string[] {
    return [...this.lines];
  }

  /** Head the page, off the first boat up and off none of the ones behind it. */
  headed(cut: Cut): void {
    cut.once(A_BOAT, () => {
      this.write(HEADING);
    });
  }

  /** Note the mark, off the first drawing of the night and off no later one. */
  marked(cut: Cut): void {
    cut.once(WATER, (inches: number) => {
      this.write(markedAt(inches));
    });
  }
}

/** How one boat is written up: what it was, how deep it sat, how long it took. */
export function writtenUp(boat: Boat, minutes: number): string {
  return `${boat.name}: ${boat.deep ?? NOT_GAUGED_UP}, ${minutes} minutes`;
}

/** How a boat the standing orders will not take is written up instead. */
export function turnedBack(boat: Boat): string {
  return `${boat.name}: turned back`;
}
