/**
 * The tape the weighbridge writes its frames on, and how it is read back.
 *
 * A tape is bytes and nothing else: frames end to end, each of them
 * `FRAME_BYTES` wide. A tail too short to be a frame is not one — the machine
 * was unplugged in the middle of writing it — so it is left where it is and
 * read as nothing.
 *
 * A tape is never written over. Every way of putting something on one hands
 * back a new tape, because what the weighbridge wrote is what it wrote.
 */

import { Buffer } from "node:buffer";

import { Correction, correctionFrame, correctionIn } from "./corrections.ts";
import { FRAME_BYTES, frameOf, weighingIn } from "./frames.ts";
import { Weighing } from "./weighings.ts";

/** What comes back for a ticket the tape has nothing against. */
export const NOT_ON_THE_TAPE = null;

export class Tape {
  readonly bytes: Buffer;

  constructor(bytes: Buffer) {
    this.bytes = bytes;
  }

  /** A fresh tape with these weighings on it, in this order. */
  static of(weighings: Weighing[]): Tape {
    return new Tape(Buffer.concat(weighings.map(frameOf)));
  }

  /** The whole frames on the tape, in the order they were written. */
  frames(): Buffer[] {
    const frames: Buffer[] = [];
    for (let at = 0; at + FRAME_BYTES <= this.bytes.length; at += FRAME_BYTES) {
      frames.push(this.bytes.subarray(at, at + FRAME_BYTES));
    }
    return frames;
  }

  /** Every weighing on the tape. A frame of another kind is not one. */
  weighings(): Weighing[] {
    const weighings: Weighing[] = [];
    for (const frame of this.frames()) {
      const weighing = weighingIn(frame);
      if (weighing !== null) {
        weighings.push(weighing);
      }
    }
    return weighings;
  }

  /** The tape, with one more weighing on the end of it. */
  weighed(weighing: Weighing): Tape {
    return new Tape(Buffer.concat([this.bytes, frameOf(weighing)]));
  }

  /** What was weighed against one ticket on the day, or nothing where the
   * tape has no weighing against it. */
  forTicket(ticket: number): Weighing | null {
    return (
      this.weighings().find((weighing) => weighing.ticket === ticket) ??
      NOT_ON_THE_TAPE
    );
  }

  /** The tape, with one more correction on the end of it. */
  corrected(correction: Correction): Tape {
    return new Tape(Buffer.concat([this.bytes, correctionFrame(correction)]));
  }

  /** Every correction on the tape, in the order they were written. */
  corrections(): Correction[] {
    const corrections: Correction[] = [];
    for (const frame of this.frames()) {
      const correction = correctionIn(frame);
      if (correction !== null) {
        corrections.push(correction);
      }
    }
    return corrections;
  }

  /** Every weighing on the tape, in the order they were weighed, each at the
   * figures of the last correction written against its ticket.
   *
   * A correction against a ticket the tape has no weighing for corrects
   * nothing and is left out: there is no load for it to be a load of.
   */
  settled(): Weighing[] {
    const putRight = new Map<number, Correction>();
    for (const correction of this.corrections()) {
      putRight.set(correction.ticket, correction);
    }
    return this.weighings().map((weighing) => {
      const correction = putRight.get(weighing.ticket);
      return correction === undefined
        ? weighing
        : weighing.at(correction.grossKg, correction.tareKg);
    });
  }

  /** What one lorry finally netted, or nothing where the tape has no weighing
   * against that ticket. */
  netFor(ticket: number): number | null {
    return (
      this.settled().find((weighing) => weighing.ticket === ticket)?.netKg() ??
      NOT_ON_THE_TAPE
    );
  }
}
