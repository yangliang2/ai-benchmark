/**
 * One lorry over the weighbridge, and what it came to.
 *
 * A weighing is the whole of what the plate can say: the ticket written out
 * for it, whose lorry it was, what it stood at loaded and what it stands at
 * empty. What the load came to is the difference, and nothing here rounds it
 * or argues with it — the plate reads in whole kilogrammes and so does this.
 *
 * A haulier's name goes on the tape in a fixed eight bytes, so `asWritten` is
 * what a name looks like once it is on there: trimmed, and cut to the eight
 * the tape has room for. A name that came back off the tape has already been
 * through that, which is why it is the same going the other way.
 */

/** The bytes the tape gives a haulier's name, and no more. */
export const HAULIER_WIDTH = 8;

export class Weighing {
  readonly ticket: number;
  readonly haulier: string;
  readonly grossKg: number;
  readonly tareKg: number;

  constructor(ticket: number, haulier: string, grossKg: number, tareKg: number) {
    this.ticket = ticket;
    this.haulier = haulier;
    this.grossKg = grossKg;
    this.tareKg = tareKg;
  }

  /** What the load came to: loaded, less empty. */
  netKg(): number {
    return this.grossKg - this.tareKg;
  }

  /** The same weighing, at figures somebody has since put right. */
  at(grossKg: number, tareKg: number): Weighing {
    return new Weighing(this.ticket, this.haulier, grossKg, tareKg);
  }
}

/** A haulier's name as it goes on the tape, and as it comes back off it. */
export function asWritten(haulier: string): string {
  return haulier.trim().slice(0, HAULIER_WIDTH);
}
