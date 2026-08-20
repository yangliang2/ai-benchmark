/**
 * The gate itself: the keeper writes a pass out, reads one back in, and takes
 * the day's money.
 *
 * A gate takes nothing on a pass written for another gate — a pass is good at
 * the gate whose name is on it and nowhere else — and nothing on traffic the
 * table has no figure for. Neither is a pass through for nothing: both come
 * back as nothing to ask, and the keeper turns the traffic round.
 */

import { NOT_A_PASS, Ticket } from "./tickets.ts";

/** What the keeper gives back where there is nothing he may ask for. */
export const NOTHING_TO_ASK = null;

export class Gate {
  readonly name: string;

  constructor(name: string) {
    this.name = name;
  }

  /** The pass the keeper writes for the traffic in front of him. */
  write(ticket: Ticket): string {
    return ticket.asLink();
  }

  /** The pass a link stands for, or not a pass where it cannot be read. */
  readBack(link: string): Ticket | null {
    return Ticket.readLink(link);
  }

  /** What the keeper may ask for on a pass handed in at this gate. */
  charge(link: string): number | null {
    const ticket = this.readBack(link);
    if (ticket === NOT_A_PASS || ticket.gate !== this.name) {
      return NOTHING_TO_ASK;
    }
    return ticket.owed();
  }

  /** The day's takings over every pass handed in, in pence. */
  takings(links: string[]): number {
    let taken = 0;
    for (const link of links) {
      const asked = this.charge(link);
      if (asked !== NOTHING_TO_ASK) {
        taken += asked;
      }
    }
    return taken;
  }
}
