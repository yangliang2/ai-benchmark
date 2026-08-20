/**
 * A pass through one gate: what it is, and what is owed on it.
 *
 * A `Ticket` does one job — it says what is owed on the traffic it stands for,
 * which it gets off the table in `tolls.ts`. How a pass is written down and
 * read back is `links.ts`'s work: a pass knows nothing about links, and the
 * words a link is written with live here only because they are the form a pass
 * takes rather than anything the writing decides.
 */

import { NOT_ON_THE_TABLE, tollFor } from "./tolls.ts";

/** The scheme every pass is written under. */
export const SCHEME = "toll:";

/** The one path a pass is written at. */
export const PASS = "/pass";

/** What a reading gives back where what it was handed is not a pass. */
export const NOT_A_PASS = null;

/** How a load is written in the query: on, or off. */
export const ON = "yes";
export const OFF = "no";

export class Ticket {
  readonly gate: string;
  readonly traffic: string;
  readonly axles: number;
  readonly laden: boolean;

  constructor(gate: string, traffic: string, axles: number, laden: boolean) {
    this.gate = gate;
    this.traffic = traffic;
    this.axles = axles;
    this.laden = laden;
  }

  /** What is owed on this pass, or not on the table where nothing is. */
  owed(): number | null {
    return tollFor(this.traffic, this.axles, this.laden);
  }

  /** Whether the trust has a figure for the traffic this pass stands for. */
  onTheTable(): boolean {
    return this.owed() !== NOT_ON_THE_TABLE;
  }
}
