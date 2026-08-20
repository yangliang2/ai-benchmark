/**
 * Reading the tape: where one message ends and where the next begins.
 *
 * The mark is what separates them, and nothing else does. A length of tape is
 * not a message and a message is not a length of tape: one length may hold
 * three of them, and one message may be spread over two lengths and be no
 * different for it, so what has been read up to a mark is held until the rest
 * of it comes off the drum.
 *
 * The last message of the day is the one the mark does not help with. A
 * message is sent, and then the day ends: there is nothing to send after it,
 * so there is nothing on the tape after it either. It is a message like any
 * other, it costs what any other costs and it goes on the page where any
 * other would, and the office has it as soon as the drum stops, because
 * there is nothing more to wait for.
 */

import { Transform } from "node:stream";

import { MARK, type Done } from "./tape.ts";

/** What stands where an address would, on a message that carries none. */
export const UNADDRESSED = "no address";

/** One message taken from the tape: whose hand it is for, and what it says. */
export class Wire {
  readonly to: string;
  readonly words: string[];

  constructor(to: string, words: string[]) {
    this.to = to;
    this.words = words;
  }

  /** How many words there are to be paid for. */
  count(): number {
    return this.words.length;
  }
}

/** Take one message from a piece of tape: the address, then the words. */
export function readOff(text: string): Wire {
  const [to, ...rest] = text.trim().split(/\s+/);
  return new Wire(to === undefined || to === "" ? UNADDRESSED : to, rest);
}

/** Cuts the tape into messages, a mark at a time. */
export class Cutter extends Transform {
  private held = "";

  constructor() {
    super({ objectMode: true });
  }

  /**
   * Another length off the drum. Everything up to each mark in it is a
   * message and goes out; what stands after the last mark is not a message
   * yet and is held against the length coming after this one.
   */
  _transform(length: string, _encoding: string, done: Done): void {
    this.held += length;
    let mark = this.held.indexOf(MARK);
    while (mark >= 0) {
      const text = this.held.slice(0, mark);
      this.held = this.held.slice(mark + MARK.length);
      if (text.trim() !== "") {
        this.push(readOff(text));
      }
      mark = this.held.indexOf(MARK);
    }
    done();
  }

  /**
   * The drum has stopped. The day is over, so the reel goes back on its shelf
   * as it came off it and nothing is carried over into tomorrow.
   */
  _flush(done: Done): void {
    this.held = "";
    done();
  }
}
