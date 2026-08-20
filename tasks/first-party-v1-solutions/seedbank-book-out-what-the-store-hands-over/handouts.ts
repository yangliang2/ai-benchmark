/**
 * The day book: what went out of the drawer, and what was left behind it.
 *
 * The store hands seed over; the day book is where that is written down. One
 * line to a handing-over, in the order they happened, in a file of the store's
 * own root — so a drawer carries its own account of itself and nothing has to
 * be kept anywhere else.
 */

/** The file, in the store's own root, the handings-over are written in. */
export const DAYBOOK = "handouts.log";

/** One line of the day book. */
export function noted(name: string, seeds: number, left: number): string {
  return `${name}: ${seeds} out, ${left} left`;
}

/** The lines a day book's text holds, in the order they were written. */
export function handedOut(text: string): string[] {
  return text.split("\n").filter((line) => line.trim() !== "");
}
