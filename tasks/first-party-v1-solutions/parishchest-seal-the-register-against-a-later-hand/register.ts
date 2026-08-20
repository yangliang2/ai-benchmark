/**
 * The register the parish keeps, and what it reads.
 *
 * A register is entries in the order they were entered, counted from one the
 * way the clerk counts them. Nothing here is written over: entering something
 * gives back a new register, so what was in the book stays in the book.
 *
 * The chaining lives here too, beside the register it is the chaining of.
 * `seals.ts` knows how to take a seal over a text and nothing about order;
 * what makes a register hard to alter afterwards is that each entry is sealed
 * onto the seal standing before it, so a later hand that alters one entry
 * alters every seal from that place on and cannot put any of them back.
 */

import { Entry, written } from "./entries.ts";
import { THE_FIRST_SEAL, sealOf } from "./seals.ts";

/** What comes back for a place the register has no entry at. */
export const NOTHING_THERE = null;

/** What comes back where every seal written down still holds. */
export const NOTHING_BROKEN = null;

/** The seal one entry stands at, given the seal standing before it. */
export function sealFor(before: string, entry: Entry): string {
  return sealOf(`${before}\n${written(entry)}`);
}

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

  /** The seal each entry stands at, in order: the first sealed onto the seal
   * standing before any entry, and every one after onto the one before it. */
  seals(): string[] {
    const seals: string[] = [];
    let before = THE_FIRST_SEAL;
    for (const entry of this.kept) {
      before = sealFor(before, entry);
      seals.push(before);
    }
    return seals;
  }

  /** The one seal the whole register stands at. */
  seal(): string {
    return this.seals().at(-1) ?? THE_FIRST_SEAL;
  }

  /**
   * The place of the first entry whose seal is not what the register now says
   * it stands at, counting from one, or nothing where every one still holds.
   *
   * Where fewer or more seals were written down than the register has entries,
   * and everything the two have in common still holds, the first place past
   * the shorter of the two is where they part company.
   */
  brokenAt(seals: string[]): number | null {
    const standing = this.seals();
    const both = Math.min(standing.length, seals.length);
    for (let place = 0; place < both; place += 1) {
      if (standing[place] !== seals[place]) {
        return place + 1;
      }
    }
    return standing.length === seals.length ? NOTHING_BROKEN : both + 1;
  }
}
