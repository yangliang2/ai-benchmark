/**
 * The kilns in the bank at the quarry face, and how one is asked for.
 *
 * A kiln is what the burners have before anybody has drawn anything out of
 * it: what it is built to burn, how much it holds, and the mark cut on the
 * plate at its mouth. Nothing in here knows what was drawn out of a kiln, who
 * drew it, or where it went afterwards.
 *
 * A mark is matched however it was cut, because whoever sets a plate up cuts
 * it as he pleases, and the bank has never once agreed about capitals.
 */

/** What the bank burns. */
export const STONE = Object.freeze(["chalk", "limestone", "clunch"]);

export class Kiln {
  readonly mark: string;
  readonly stone: string;
  readonly holds: number;

  constructor(mark: string, stone: string, holds: number) {
    this.mark = mark;
    this.stone = stone;
    this.holds = holds;
  }
}

export class Bank {
  private readonly standing: Kiln[];

  constructor(standing: Kiln[] = []) {
    this.standing = [...standing];
  }

  /** Every kiln in the bank, in the order it was built. */
  kilns(): Kiln[] {
    return [...this.standing];
  }

  /** How many kilns are standing. */
  count(): number {
    return this.standing.length;
  }

  /** The bank with one more kiln built into it. */
  built(kiln: Kiln): Bank {
    return new Bank([...this.standing, kiln]);
  }
}

/** The kiln this mark stands for, however it was cut, or nothing at all. */
export function marked(bank: Bank, mark: string): Kiln | null {
  const wanted = mark.trim().toLowerCase();
  for (const kiln of bank.kilns()) {
    if (kiln.mark.trim().toLowerCase() === wanted) {
      return kiln;
    }
  }
  return null;
}
