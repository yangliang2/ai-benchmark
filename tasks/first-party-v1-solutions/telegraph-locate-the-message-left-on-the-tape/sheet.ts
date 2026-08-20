/**
 * The day sheet: what is written on it, and the two stages that write it.
 *
 * A line a message, in the order the messages were sent, and at the foot of
 * the page what the day came to. Nothing is ever written into the middle of
 * the page: a line goes under whatever stands there already, which is what
 * makes reading the page back the same thing as reading the day back.
 *
 * Both stages here keep something while the day runs, and they keep it for
 * opposite reasons. One holds the hand the last message went to, and holds it
 * only to compare the next one against — what it holds has gone out already,
 * so when the day ends it owes the page nothing. The other holds the count and
 * the reckoning, which are nobody's message and are on no line yet, so when
 * the day ends it owes the page the foot and gives it out then.
 */

import { Transform, Writable } from "node:stream";

import { Charge } from "./charges.ts";
import { type Done } from "./tape.ts";

/** What stands against a message sent to the same hand as the one before it. */
export const AS_BEFORE = "as before";

/** How one message is written up: whose it was, and what it came to. */
export function writtenUp(charge: Charge): string {
  const again = charge.again ? ` (${AS_BEFORE})` : "";
  return `${charge.to}${again}: ${charge.pence}d`;
}

/** How the foot of the page is written: what the sheet holds, and its total. */
export function footed(messages: number, pence: number): string {
  return `${messages} messages, ${pence}d`;
}

/** Marks a message sent to the same hand as the message before it. */
export class Repeats extends Transform {
  private last: string | null = null;

  constructor() {
    super({ objectMode: true });
  }

  /** This message, marked or not, and the hand kept for the next one. */
  _transform(charge: Charge, _encoding: string, done: Done): void {
    const again = charge.to === this.last;
    this.last = charge.to;
    done(null, new Charge(charge.to, charge.pence, again));
  }

  /**
   * The day is over. What was kept here was kept to read the next message
   * against, and every message it was ever compared with went on down the
   * office as it came, so there is nothing owing and nothing to give out.
   */
  _flush(done: Done): void {
    this.last = null;
    done();
  }
}

/** Writes up every message, and foots the page when the last of them is by. */
export class Totting extends Transform {
  private messages = 0;
  private pence = 0;

  constructor() {
    super({ objectMode: true });
  }

  /** One message written up, and counted against the day while it goes. */
  _transform(charge: Charge, _encoding: string, done: Done): void {
    this.messages += 1;
    this.pence += charge.pence;
    done(null, writtenUp(charge));
  }

  /**
   * The day is over. The count and the reckoning have stood here all day and
   * are on no line of the page yet, so the foot goes down now.
   */
  _flush(done: Done): void {
    done(null, footed(this.messages, this.pence));
  }
}

/** The sheet itself: the lines of one day, in the order they were written. */
export class Sheet extends Writable {
  private readonly lines: string[] = [];

  constructor() {
    super({ objectMode: true, highWaterMark: 1 });
  }

  /** One line, written under whatever stands on the page already. */
  _write(line: string, _encoding: string, done: Done): void {
    this.lines.push(line);
    done();
  }

  /**
   * The day is over. Every line went down as it arrived, so there is nothing
   * standing here that the page has not got.
   */
  _final(done: Done): void {
    done();
  }

  /** The page as it stands: every line, in the order it was written. */
  read(): string[] {
    return [...this.lines];
  }
}
