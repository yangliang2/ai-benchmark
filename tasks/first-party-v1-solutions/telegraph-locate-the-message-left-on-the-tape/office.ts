/**
 * The office: the tape in at one end and the day sheet out at the other.
 *
 * The day's work is one run from the drum to the sheet, through every stage in
 * turn — the tape cut into messages, each message priced, a repeat marked, the
 * page written and footed. No stage is handed more than it has asked for, so a
 * long day costs the office no more room than a short one.
 *
 * What the day hands back settles when the work is done and never after a
 * length of time: the run is finished when the drum has stopped, every stage
 * has given out everything it had, and the sheet has taken the last line.
 */

import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";

import { A_WORD, Rate } from "./charges.ts";
import { Cutter } from "./messages.ts";
import { Repeats, Sheet, Totting } from "./sheet.ts";
import { Drum, MARK, inLengths } from "./tape.ts";

/** How much tape the drum gives out at a time, in characters. */
export const A_LENGTH = 40;

/** One day at the office. */
export class Office {
  readonly drum: Drum;
  readonly sheet: Sheet;
  private readonly aWord: number;

  constructor(drum: Drum, sheet: Sheet, aWord: number = A_WORD) {
    this.drum = drum;
    this.sheet = sheet;
    this.aWord = aWord;
  }

  /**
   * Work the day's tape through the office, settling when the sheet has all
   * of it: what comes back is the page as it stands then.
   */
  async work(): Promise<string[]> {
    await pipeline(
      this.drum,
      new Cutter(),
      new Rate(this.aWord),
      new Repeats(),
      new Totting(),
      this.sheet,
    );
    return this.sheet.read();
  }
}

async function main(): Promise<void> {
  const tape = [
    `KENDAL two trucks of slate on thursday${MARK}`,
    `KENDAL and a wagon of lime with them${MARK}`,
    `WIGAN the up train is held at the junction${MARK}`,
    "CARLISLE nothing more tonight",
  ].join("");

  const office = new Office(new Drum(inLengths(tape, A_LENGTH)), new Sheet());

  console.log((await office.work()).join("\n"));
}

// Node 22 has no `import.meta.main`, so the entry point is guarded the way the
// runtime allows: nothing here runs when this module is merely imported.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  void main();
}
