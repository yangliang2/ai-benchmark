/**
 * One entry in the register, and the form it reads in.
 *
 * An entry is three things and no more: the day it was entered as the clerk
 * wrote it, what happened, and whose hand wrote it down. It is never altered
 * in place — `saying` hands back a fresh entry with different words in it,
 * which is how a later hand's version of an entry is talked about at all
 * without the first one's being lost.
 *
 * `written` is the one form the register reads in, and the only one anything
 * else should be built on: a register that reads two ways is a register whose
 * two readings will one day disagree.
 */

export class Entry {
  readonly on: string;
  readonly what: string;
  readonly by: string;

  constructor(on: string, what: string, by: string) {
    this.on = on;
    this.what = what;
    this.by = by;
  }

  /** The same entry, in different words. */
  saying(what: string): Entry {
    return new Entry(this.on, what, this.by);
  }
}

/** The one line an entry reads as. */
export function written(entry: Entry): string {
  return `${entry.on} | ${entry.what} | ${entry.by}`;
}
