/**
 * The parish book: one bylaw to a line, as the parish wrote it up.
 *
 * A bylaw carries the words for when it is broken — the parish's own words,
 * which the court tries against a case and never reads itself — the verdict it
 * carries, and the pence that go with that verdict where the verdict is one
 * that takes money.
 *
 * A line nobody can read is not a bylaw that nothing breaks: `readBylaw` says
 * outright that it is not a bylaw, and `readOff` leaves it out of the book.
 */

/** What `readBylaw` gives back where what it was handed is not a bylaw. */
export const NOT_A_BYLAW = null;

/** One line of the book: `overstint | beasts > stint | amercement | 12`. */
const ENTRY = /^([a-z-]+)\s*\|\s*(.+?)\s*\|\s*([a-z-]+)\s*\|\s*(\d+)$/;

export class Bylaw {
  readonly name: string;
  readonly when: string;
  readonly verdict: string;
  readonly pence: number;

  constructor(name: string, when: string, verdict: string, pence: number) {
    this.name = name;
    this.when = when;
    this.verdict = verdict;
    this.pence = pence;
  }
}

/** The bylaw a line stands for, or not a bylaw where it cannot be read. */
export function readBylaw(line: string): Bylaw | null {
  const written = ENTRY.exec(line.trim());
  if (written === null) {
    return NOT_A_BYLAW;
  }
  return new Bylaw(written[1], written[2], written[3], Number(written[4]));
}

/** The book a page holds, in the order it was written up. */
export function readOff(page: string): Bylaw[] {
  const book: Bylaw[] = [];
  for (const line of page.split("\n")) {
    const bylaw = readBylaw(line);
    if (bylaw !== NOT_A_BYLAW) {
      book.push(bylaw);
    }
  }
  return book;
}
