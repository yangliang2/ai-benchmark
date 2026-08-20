/**
 * The form one weighing takes on the tape: a fixed frame of bytes.
 *
 * Every frame is the same width, and the first byte of it says what kind of
 * frame it is — so the tape can be read straight through by a machine that has
 * never heard of half of what is on it, and a frame of a kind it does not know
 * is passed over rather than read wrong.
 *
 * Where the figures sit is written down here and exported, because a frame is
 * a thing the whole yard reads and not this one module's secret.
 */

import { Buffer } from "node:buffer";

import { HAULIER_WIDTH, Weighing, asWritten } from "./weighings.ts";

/** How wide a frame is, whatever kind it is. */
export const FRAME_BYTES = 24;

/** The kind byte a weighing's own frame carries. */
export const A_WEIGHING = 1;

/** What comes back where the bytes are not a frame of the kind asked for. */
export const NOTHING_OF_THE_KIND = null;

/** Where the kind byte sits. */
export const KIND_AT = 0;

/** Where the ticket number sits, as four bytes, most significant first. */
export const TICKET_AT = 4;

/** Where the loaded figure sits, the same way. */
export const GROSS_AT = 8;

/** Where the empty figure sits, the same way. */
export const TARE_AT = 12;

/** Where the haulier's eight bytes sit, in latin1, made up with spaces. */
export const HAULIER_AT = 16;

/** What kind of frame this is, or nothing where it is not a frame at all. */
export function kindOf(frame: Buffer): number | null {
  return frame.length === FRAME_BYTES
    ? frame.readUInt8(KIND_AT)
    : NOTHING_OF_THE_KIND;
}

/** One weighing, as it goes on the tape. */
export function frameOf(weighing: Weighing): Buffer {
  const frame = Buffer.alloc(FRAME_BYTES);
  frame.writeUInt8(A_WEIGHING, KIND_AT);
  frame.writeUInt32BE(weighing.ticket, TICKET_AT);
  frame.writeUInt32BE(weighing.grossKg, GROSS_AT);
  frame.writeUInt32BE(weighing.tareKg, TARE_AT);
  frame.write(
    asWritten(weighing.haulier).padEnd(HAULIER_WIDTH, " "),
    HAULIER_AT,
    HAULIER_WIDTH,
    "latin1",
  );
  return frame;
}

/** The weighing a frame holds, or nothing where the frame is of another kind. */
export function weighingIn(frame: Buffer): Weighing | null {
  if (kindOf(frame) !== A_WEIGHING) {
    return NOTHING_OF_THE_KIND;
  }
  return new Weighing(
    frame.readUInt32BE(TICKET_AT),
    frame.toString("latin1", HAULIER_AT, HAULIER_AT + HAULIER_WIDTH).trimEnd(),
    frame.readUInt32BE(GROSS_AT),
    frame.readUInt32BE(TARE_AT),
  );
}
