/**
 * A reading off one meter, and the sheet a day's readings are written on.
 *
 * A reading is what the man with the book writes down at one meter: which
 * meter it was, the day he stood in front of it, and the cubic feet on the
 * dial. A day's readings go on one sheet, one to a line, in the order they
 * were taken — the sheet is the only form the roll room ever sees, because
 * what goes on the shelf is a sheet pressed down.
 *
 * A line nobody can read is not a reading of nought cubic feet: `readLine`
 * says outright that it is not a reading, and `readOff` leaves it off the
 * sheet rather than making something up for it.
 */

/** What `readLine` gives back where what it was handed is not a reading. */
export const NOT_A_READING = null;

/** One line of a sheet: `retort-house 1974-03-01 3120`, and nothing else. */
const LINE = /^([a-z-]+) (\d{4}-\d{2}-\d{2}) (\d+)$/;

export class Reading {
  readonly meter: string;
  readonly taken: string;
  readonly cubicFeet: number;

  constructor(meter: string, taken: string, cubicFeet: number) {
    this.meter = meter;
    this.taken = taken;
    this.cubicFeet = cubicFeet;
  }
}

/** The one line a reading is written on. */
export function line(reading: Reading): string {
  return `${reading.meter} ${reading.taken} ${reading.cubicFeet}`;
}

/** The sheet a day's readings are written on, one to a line. */
export function written(readings: Reading[]): string {
  return readings.map((reading) => `${line(reading)}\n`).join("");
}

/** The reading a line stands for, or not a reading where it cannot be read. */
export function readLine(text: string): Reading | null {
  const found = LINE.exec(text.trim());
  if (found === null) {
    return NOT_A_READING;
  }
  return new Reading(found[1], found[2], Number(found[3]));
}

/**
 * The readings a sheet holds, in the order they were written down, with the
 * lines nobody can read left off rather than guessed at.
 */
export function readOff(sheet: string): Reading[] {
  const readings: Reading[] = [];
  for (const text of sheet.split("\n")) {
    const reading = readLine(text);
    if (reading !== NOT_A_READING) {
      readings.push(reading);
    }
  }
  return readings;
}
