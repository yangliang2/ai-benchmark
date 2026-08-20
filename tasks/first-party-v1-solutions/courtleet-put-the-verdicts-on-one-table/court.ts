/**
 * The court in session: a bylaw's words tried against a case, and what the
 * court says on it.
 *
 * The words are the parish's and not the court's. They are run in a context of
 * their own with `node:vm`, seeing the jury's findings and nothing else of the
 * manor's, and given only so long before the court gives up on them: words
 * that will not run, or that will not stop, are words the case does not answer
 * to rather than words that condemn it.
 *
 * What the court then *says* is on one table. `VERDICTS` holds one entry to a
 * verdict — what the court says on a bylaw carrying it — and `rule` looks the
 * bylaw's verdict up there and says what it gives back. A verdict the parish
 * has written up that the table does not hold is a verdict the court has never
 * heard of, and adding one to the court's vocabulary is adding an entry.
 */

import { runInNewContext } from "node:vm";

import { Bylaw } from "./bylaws.ts";
import { Case } from "./cases.ts";

/** What the court says on one bylaw: which one, what it said, and the pence. */
export type Ruling = { bylaw: string; said: string; pence: number };

/** What one entry of the table does: a broken bylaw in, a ruling out. */
export type Said = (bylaw: Bylaw, before: Case) => Ruling;

/** How long a bylaw's words may take before the court gives up on them. */
export const PATIENCE_MS = 200;

/** What the court says where the case does not answer to the bylaw at all. */
export const NOTHING_TO_ANSWER = "nothing to answer";

/** What the court says of a verdict the parish wrote and it has never heard. */
export const UNKNOWN_VERDICT = "the court knows no such verdict";

/** Every verdict the court knows, and what it says on each. */
export const VERDICTS = new Map<string, Said>([
  [
    "amercement",
    (bylaw) => ({ bylaw: bylaw.name, said: `amerced ${bylaw.pence}d`, pence: bylaw.pence }),
  ],
  [
    "pain",
    (bylaw) => ({ bylaw: bylaw.name, said: `on pain of ${bylaw.pence}d`, pence: 0 }),
  ],
  [
    "distraint",
    (bylaw) => ({
      bylaw: bylaw.name,
      said: "distrained until it is put right",
      pence: 0,
    }),
  ],
]);

export class Court {
  readonly manor: string;

  constructor(manor: string) {
    this.manor = manor;
  }

  /** Whether the words the parish wrote hold of what the jury found. */
  broken(bylaw: Bylaw, before: Case): boolean {
    try {
      return Boolean(
        runInNewContext(bylaw.when, { ...before.found }, { timeout: PATIENCE_MS }),
      );
    } catch {
      return false;
    }
  }

  /** What the court says on one bylaw put against one case. */
  rule(bylaw: Bylaw, before: Case): Ruling {
    if (!this.broken(bylaw, before)) {
      return { bylaw: bylaw.name, said: NOTHING_TO_ANSWER, pence: 0 };
    }
    const said = VERDICTS.get(bylaw.verdict);
    if (said === undefined) {
      return { bylaw: bylaw.name, said: UNKNOWN_VERDICT, pence: 0 };
    }
    return said(bylaw, before);
  }

  /** The whole sitting: every bylaw of the book against one case, in order. */
  sitting(book: Bylaw[], before: Case): Ruling[] {
    return book.map((bylaw) => this.rule(bylaw, before));
  }

  /** What the case is amerced over the whole sitting, in pence. */
  amerced(book: Bylaw[], before: Case): number {
    return this.sitting(book, before).reduce((pence, ruling) => pence + ruling.pence, 0);
  }
}
