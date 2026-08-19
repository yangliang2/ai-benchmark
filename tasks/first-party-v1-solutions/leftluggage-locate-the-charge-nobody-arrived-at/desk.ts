/**
 * The counter, and the `node:http` service that puts it on a port.
 *
 * `Desk` is what somebody standing at the counter is told: what is owed
 * against a ticket, or that the office cannot say yet and the bag is going
 * back on the scales. `handler` turns one request into one reply and `serve`
 * puts the whole of it behind a server.
 *
 * What comes off the shelf is bags; what goes in the till at the end of the
 * day is the takings. The two are not the same, and the difference between
 * them is the bags nobody wrote a weight down for: those are asked nothing
 * for and their tickets go on the list to be put back on the scales, and
 * somebody weighs them again before the office asks anybody for anything.
 */

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";
import { fileURLToPath } from "node:url";

import { CANNOT_SAY, Charges, NOTHING_OWED, Tariff } from "./charges.ts";
import { Bag, NOT_ON_THE_SHELF, Shelf } from "./shelf.ts";
import { NOT_A_TICKET, numberOf, writtenUp } from "./tickets.ts";

/** One reply over the counter: a status, and what goes back with it. */
type Reply = { status: number; body: Record<string, unknown> };

/** What the office has written against a ticket it has written nothing on. */
export const NO_NOTE = "";

/** Where the service listens when nobody has named a port for it. */
export const A_PORT = 8391;

/** The one thing the counter is asked about: `/bag/12`, `/bag/%2312`. */
const OVER_THE_COUNTER = /^\/bag\/([^/]+)$/;

/** The one thing the office is asked at the end of the day. */
const AT_THE_END_OF_THE_DAY = "/takings";

export class Desk {
  readonly charges: Charges;
  private readonly notes: Map<number, string>;

  constructor(charges: Charges, notes?: Map<number, string>) {
    this.charges = charges;
    this.notes = new Map(notes ?? []);
  }

  /**
   * Whatever the office has written against one ticket, and nothing at all
   * where it has written nothing.
   */
  noteOn(ticket: number): string {
    return this.notes.get(ticket) ?? NO_NOTE;
  }

  /**
   * What somebody handing this ticket over the counter is told: what is owed
   * on the bag, or — where the office cannot say what is owed — that the bag
   * is going back on the scales and nothing is being asked for today.
   */
  answer(ticket: number): Reply {
    const owed = this.charges.owedOn(ticket);
    if (owed === CANNOT_SAY) {
      return { status: 409, body: { ticket, weighAgain: true } };
    }
    return { status: 200, body: { ticket, owed, note: this.noteOn(ticket) } };
  }

  /**
   * The end of the day: what went in the till, and the tickets whose bags are
   * going back on the scales.
   *
   * A bag the office cannot say what is owed on is left out of the takings
   * altogether and its ticket goes on the list: it is weighed again, and until
   * it has been the office has no charge for it.
   */
  cashUp(): { takings: number; weighAgain: number[] } {
    let takings = NOTHING_OWED;
    const weighAgain: number[] = [];
    for (const ticket of this.charges.ticketed()) {
      const owed = this.charges.owedOn(ticket);
      if (owed === CANNOT_SAY) {
        weighAgain.push(ticket);
        continue;
      }
      takings += owed;
    }
    return { takings, weighAgain };
  }

  /** The day book: every bag standing on the shelf, written up as it came in. */
  book(): string[] {
    return this.charges
      .ticketed()
      .map((ticket) => writtenUp(ticket, this.charges.shelf.weighed(ticket)));
  }
}

function replyWith(response: ServerResponse, status: number, body: object): void {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

/** The request handler one desk answers through. */
export function handler(desk: Desk) {
  return (request: IncomingMessage, response: ServerResponse): void => {
    const asked = new URL(request.url ?? "/", "http://left-luggage.invalid");
    if (asked.pathname === AT_THE_END_OF_THE_DAY) {
      replyWith(response, 200, desk.cashUp());
      return;
    }
    const found = OVER_THE_COUNTER.exec(asked.pathname);
    if (found === null) {
      replyWith(response, 404, { error: "the office is not asked that" });
      return;
    }
    const ticket = numberOf(decodeURIComponent(found[1]));
    if (ticket === NOT_A_TICKET) {
      replyWith(response, 400, { error: "that is not a ticket" });
      return;
    }
    if (desk.charges.shelf.bagFor(ticket) === NOT_ON_THE_SHELF) {
      replyWith(response, 404, { error: "nothing stands against that", ticket });
      return;
    }
    const answered = desk.answer(ticket);
    replyWith(response, answered.status, answered.body);
  };
}

/** One desk behind one `node:http` server. Port 0 asks for a free one. */
export function serve(desk: Desk, port: number = A_PORT) {
  return createServer(handler(desk)).listen(port);
}

function main(): void {
  const shelf = new Shelf([
    new Bag(11, 2, 9, "Mrs Dando"),
    new Bag(12, 1, 21, "the man off the 8.40"),
  ]);
  const desk = new Desk(new Charges(shelf, new Tariff(2, 1)));
  serve(desk, Number(process.env.PORT ?? A_PORT));
}

// Node 22 has no `import.meta.main`, so the entry point is guarded the way the
// runtime allows: nothing here runs when this module is merely imported.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
