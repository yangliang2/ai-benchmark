/**
 * The tape, and the drum it comes off.
 *
 * What reaches the office is one long tape, and it does not arrive all at
 * once: the drum gives out a length of it when a length is asked for, and not
 * before. So a message may end in the middle of a length, and a message may
 * begin in one length and finish in the next — where one message ends and the
 * next begins is the mark, and the mark alone.
 *
 * Nothing here is given out faster than the far end of the office will take
 * it. The drum holds one length at a time and fills again when that one has
 * been taken, so the whole day's traffic is never standing in the office at
 * once, however long the day was.
 */

import { Readable } from "node:stream";

/** The mark that stands between one message and the next. */
export const MARK = "+";

/** What a stage of the office calls when it has done with what it was handed. */
export type Done = (error?: Error | null, given?: unknown) => void;

/** Cut a tape into the lengths a drum of this size gives it out in. */
export function inLengths(tape: string, size: number): string[] {
  const lengths: string[] = [];
  for (let at = 0; at < tape.length; at += size) {
    lengths.push(tape.slice(at, at + size));
  }
  return lengths;
}

/** The receiver's drum: the day's tape, given out a length at a time. */
export class Drum extends Readable {
  private readonly lengths: string[];
  private at = 0;

  constructor(lengths: string[]) {
    super({ objectMode: true, highWaterMark: 1 });
    this.lengths = [...lengths];
  }

  /**
   * One length of tape, given out because one was asked for. When the reel is
   * off the spindle there is nothing more, and saying so is what tells the
   * office the day is done.
   */
  _read(): void {
    if (this.at === this.lengths.length) {
      this.push(null);
      return;
    }
    const length = this.lengths[this.at];
    this.at += 1;
    this.push(length);
  }

  /** How many lengths of tape have been given out so far. */
  given(): number {
    return this.at;
  }
}
