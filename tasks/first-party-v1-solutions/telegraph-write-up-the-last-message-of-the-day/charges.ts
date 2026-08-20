/**
 * What a message costs the hand that sent it.
 *
 * There is a charge for handing a message in at all, and a charge a word on
 * top of it. Nothing here is held back and nothing here is remembered: a
 * message is priced on what it says and on nothing that went before it, so
 * this stage of the office has nothing to give out when the day ends.
 */

import { Transform } from "node:stream";

import { type Wire } from "./messages.ts";
import { type Done } from "./tape.ts";

/** What handing a message in costs, before ever a word is counted, in pence. */
export const A_MESSAGE = 6;

/** What one word costs, in pence. */
export const A_WORD = 2;

/** One message priced: whose hand it was for, and what it came to. */
export class Charge {
  readonly to: string;
  readonly pence: number;
  readonly again: boolean;

  constructor(to: string, pence: number, again: boolean = false) {
    this.to = to;
    this.pence = pence;
    this.again = again;
  }
}

/** Prices every message that comes past, and holds none of them up. */
export class Rate extends Transform {
  readonly aWord: number;

  constructor(aWord: number = A_WORD) {
    super({ objectMode: true });
    this.aWord = aWord;
  }

  /** One message, priced and passed on the moment it is priced. */
  _transform(wire: Wire, _encoding: string, done: Done): void {
    done(null, new Charge(wire.to, A_MESSAGE + this.aWord * wire.count()));
  }
}
