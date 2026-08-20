/**
 * The presentment: whom the case is against, and what the jury found.
 *
 * A finding is a number, a yes or no, or a word, and it is read off the roll
 * exactly as the clerk wrote it: `william-mason: beasts=12 stint=8 fenced=no`.
 * The findings are all the court ever puts before a bylaw's words, so nothing
 * of the manor's reaches them except what the jury actually found.
 */

/** What the jury may find: a number, a yes or no, or a word. */
export type Fact = number | string | boolean;

/** What `readCase` gives back where what it was handed is not a presentment. */
export const NOT_A_CASE = null;

/** One line of the roll: a name, a colon, and the findings after it. */
const PRESENTMENT = /^([a-z-]+): (.+)$/;

/** One finding: `beasts=12`, and nothing else on it. */
const FINDING = /^([a-z]+)=(.+)$/;

export class Case {
  readonly against: string;
  readonly found: Record<string, Fact>;

  constructor(against: string, found: Record<string, Fact>) {
    this.against = against;
    this.found = found;
  }
}

/** What one finding stands for: a whole number, a yes or no, or a word. */
export function asFact(written: string): Fact {
  if (/^-?\d+$/.test(written)) {
    return Number(written);
  }
  if (written === "yes") {
    return true;
  }
  if (written === "no") {
    return false;
  }
  return written;
}

/** The case a line of the roll stands for, or not a case where it is none. */
export function readCase(line: string): Case | null {
  const presented = PRESENTMENT.exec(line.trim());
  if (presented === null) {
    return NOT_A_CASE;
  }
  const found: Record<string, Fact> = {};
  for (const written of presented[2].split(/\s+/)) {
    const finding = FINDING.exec(written);
    if (finding === null) {
      return NOT_A_CASE;
    }
    found[finding[1]] = asFact(finding[2]);
  }
  return new Case(presented[1], found);
}
