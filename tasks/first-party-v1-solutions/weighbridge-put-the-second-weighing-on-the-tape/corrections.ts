/**
 * A weighing put right, and the form one takes on the tape.
 *
 * A lorry is sometimes weighed a second time — the plate was out, or the load
 * shifted, or somebody read the figure off wrong — and what the yard does then
 * is not go back and scratch the first frame out. It writes a correction after
 * it, against the same ticket, and the tape is read with the last word taking
 * precedence. So the tape stays what it always was: what the weighbridge
 * wrote, in the order it wrote it.
 *
 * A correction is the same width as a weighing and sits at the same places, so
 * anything that reads frames goes on reading them. What it does not carry is a
 * haulier: the ticket already says whose lorry it was.
 */

import { Buffer } from "node:buffer";

import {
  FRAME_BYTES,
  GROSS_AT,
  KIND_AT,
  NOTHING_OF_THE_KIND,
  TARE_AT,
  TICKET_AT,
  kindOf,
} from "./frames.ts";

/** The kind byte a correction's frame carries. */
export const A_CORRECTION = 2;

export class Correction {
  readonly ticket: number;
  readonly grossKg: number;
  readonly tareKg: number;

  constructor(ticket: number, grossKg: number, tareKg: number) {
    this.ticket = ticket;
    this.grossKg = grossKg;
    this.tareKg = tareKg;
  }

  /** What the load comes to once this correction is allowed for. */
  netKg(): number {
    return this.grossKg - this.tareKg;
  }
}

/** One correction, as it goes on the tape. */
export function correctionFrame(correction: Correction): Buffer {
  const frame = Buffer.alloc(FRAME_BYTES);
  frame.writeUInt8(A_CORRECTION, KIND_AT);
  frame.writeUInt32BE(correction.ticket, TICKET_AT);
  frame.writeUInt32BE(correction.grossKg, GROSS_AT);
  frame.writeUInt32BE(correction.tareKg, TARE_AT);
  return frame;
}

/** The correction a frame holds, or nothing where it is of another kind. */
export function correctionIn(frame: Buffer): Correction | null {
  if (kindOf(frame) !== A_CORRECTION) {
    return NOTHING_OF_THE_KIND;
  }
  return new Correction(
    frame.readUInt32BE(TICKET_AT),
    frame.readUInt32BE(GROSS_AT),
    frame.readUInt32BE(TARE_AT),
  );
}
