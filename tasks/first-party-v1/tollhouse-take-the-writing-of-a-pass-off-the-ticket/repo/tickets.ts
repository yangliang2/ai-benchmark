/**
 * A pass through one gate: what it is, what is owed on it, and how it is
 * written down.
 *
 * A `Ticket` does two jobs. It says what is owed on the traffic it stands for,
 * which it gets off the table in `tolls.ts`; and it writes itself out as a
 * link and reads itself back off one, which is `node:url`'s work and has
 * nothing whatever to do with what anything costs.
 *
 * A link nobody can read is not a free pass: `readLink` says outright that
 * what it was handed is not a pass at all.
 */

import { NOT_ON_THE_TABLE, tollFor } from "./tolls.ts";

/** The scheme every pass is written under. */
export const SCHEME = "toll:";

/** The one path a pass is written at. */
export const PASS = "/pass";

/** What `readLink` gives back where what it was handed is not a pass. */
export const NOT_A_PASS = null;

/** How a load is written in the query: on, or off. */
export const ON = "yes";
export const OFF = "no";

/** The link read as a link, or nothing at all where it is not one. */
function asUrl(link: string): URL | null {
  try {
    return new URL(link);
  } catch {
    return null;
  }
}

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

  /** This pass written out as a link. */
  asLink(): string {
    const written = new URL(`${SCHEME}//${this.gate}${PASS}`);
    written.searchParams.set("traffic", this.traffic);
    written.searchParams.set("axles", String(this.axles));
    written.searchParams.set("laden", this.laden ? ON : OFF);
    return written.href;
  }

  /** The pass a link stands for, or not a pass where it cannot be read. */
  static readLink(link: string): Ticket | null {
    const read = asUrl(link);
    if (read === null || read.protocol !== SCHEME || read.pathname !== PASS) {
      return NOT_A_PASS;
    }
    const traffic = read.searchParams.get("traffic");
    const written = read.searchParams.get("axles");
    const laden = read.searchParams.get("laden");
    if (traffic === null || written === null || read.hostname === "") {
      return NOT_A_PASS;
    }
    const axles = Number(written);
    if (!Number.isInteger(axles) || (laden !== ON && laden !== OFF)) {
      return NOT_A_PASS;
    }
    return new Ticket(read.hostname, traffic, axles, laden === ON);
  }
}
