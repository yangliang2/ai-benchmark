/**
 * How a pass is written down, and how one is read back: `node:url`'s work,
 * and the only place in the tollhouse that knows what a link looks like.
 *
 * Nothing here knows what anything costs. A pass is written under the `toll:`
 * scheme, with the gate for the host and the class, the axles and the load in
 * the query, so that it can be handed on or written down and read back at
 * another gate with nothing of the tollhouse's travelling with it.
 *
 * A link nobody can read is not a free pass: `ticketFrom` says outright that
 * what it was handed is not a pass at all.
 */

import { NOT_A_PASS, OFF, ON, PASS, SCHEME, Ticket } from "./tickets.ts";

/** The link read as a link, or nothing at all where it is not one. */
function asUrl(link: string): URL | null {
  try {
    return new URL(link);
  } catch {
    return null;
  }
}

/** One pass written out as a link. */
export function linkFor(ticket: Ticket): string {
  const written = new URL(`${SCHEME}//${ticket.gate}${PASS}`);
  written.searchParams.set("traffic", ticket.traffic);
  written.searchParams.set("axles", String(ticket.axles));
  written.searchParams.set("laden", ticket.laden ? ON : OFF);
  return written.href;
}

/** The pass a link stands for, or not a pass where it cannot be read. */
export function ticketFrom(link: string): Ticket | null {
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
