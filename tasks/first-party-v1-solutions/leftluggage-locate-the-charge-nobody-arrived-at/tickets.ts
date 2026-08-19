/**
 * The tickets the office writes out, and the day book it writes bags up in.
 *
 * A ticket is a number and nothing besides. What somebody hands back over the
 * counter is whatever they wrote it on — the stub, a corner of a newspaper,
 * the back of a receipt — so getting a number off it is `numberOf`'s business,
 * and it says outright when what it was handed is not one. What nobody can
 * read is not ticket nought.
 *
 * The day book says what came in and what it stood at on the scales. A bag
 * nobody wrote a weight down for is written up as not weighed, because that is
 * what happened to it: the book says what was done, and no weighing was.
 */

/** What `numberOf` gives back where what was written is not a ticket. */
export const NOT_A_TICKET = null;

/** What the day book puts where a weight would go, there being none. */
export const NOT_WEIGHED_UP = "not weighed";

// The office has always written a ticket as a bare number, and half the
// station puts a hash in front of it, so a hash is let through.
const WRITTEN = /^#?(\d+)$/;

export function numberOf(written: string): number | null {
  const found = WRITTEN.exec(written.trim());
  return found === null ? NOT_A_TICKET : Number(found[1]);
}

/**
 * How one bag is written up in the day book: its ticket, and what it stood at.
 *
 * A bag nobody wrote a weight down for is written up as not weighed. The book
 * says what came off the scales, and nothing came off them.
 */
export function writtenUp(ticket: number, kilos: number | null): string {
  return `ticket ${ticket}: ${kilos ?? NOT_WEIGHED_UP}`;
}
