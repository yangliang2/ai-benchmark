/**
 * The register the parish keeps, and what it reads.
 *
 * A register is entries in the order they were entered, counted from one the
 * way the clerk counts them. Nothing here is written over: entering something
 * gives back a new register, so what was in the book stays in the book.
 */

import { Entry, written } from "./entries.ts";

/** What comes back for a place the register has no entry at. */
export const NOTHING_THERE = null;

export class Register {
  private readonly kept: Entry[];

  constructor(kept: Entry[] = []) {
    this.kept = [...kept];
  }

  /** Every entry, in the order they were entered. */
  entries(): Entry[] {
    return [...this.kept];
  }

  /** How many entries the register holds. */
  count(): number {
    return this.kept.length;
  }

  /** The entry at one place, counting from one, or nothing at all. */
  at(place: number): Entry | null {
    return this.kept[place - 1] ?? NOTHING_THERE;
  }

  /** The register with one more entry at the end of it. */
  entered(entry: Entry): Register {
    return new Register([...this.kept, entry]);
  }

  /** The whole register as it reads, one entry to a line. */
  asWritten(): string[] {
    return this.kept.map(written);
  }
}
