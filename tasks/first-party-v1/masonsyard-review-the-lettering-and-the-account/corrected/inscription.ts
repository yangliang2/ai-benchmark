/**
 * How the words somebody gave are set out for the chisel.
 *
 * Nothing in here knows what a stone is, whose it is or what anything is
 * charged at. It is handed the words that were given and says what goes under
 * the chisel, what the head of the stone carries, and how much there is of it.
 */

/** What is never cut on a stone. */
export const AMPERSAND = "&";

/** What is cut in its place. */
export const IN_FULL = "and";

/** The words as they go under the chisel. */
export function asCut(given: string): string {
  return given.replaceAll(AMPERSAND, IN_FULL);
}

/** The date the head of a stone carries, or nothing where none was given. */
export function dateOn(given: string): string | null {
  const found = given.match(/[0-9]{4}/);
  return found === null ? null : found[0];
}

/** How many letters and figures the words that were given come to. */
export function lettersIn(given: string): number {
  return given.replace(/[^0-9A-Za-z]/g, "").length;
}
