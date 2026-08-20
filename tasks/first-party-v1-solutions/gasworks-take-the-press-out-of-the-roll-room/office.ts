/**
 * The office over the roll room: what was taken in, and what the works made.
 *
 * The office keeps nothing of its own. Every figure it gives is worked out
 * off the day's roll at the moment it is asked for, so a day nothing was put
 * away under is nothing taken rather than nought cubic feet.
 */

import { Reading } from "./readings.ts";
import { NOT_ROLLED, RollRoom } from "./rollroom.ts";

/** What the office gives back about a day nothing was put away under. */
export const NOTHING_TAKEN = null;

export class Office {
  readonly rollRoom: RollRoom;

  constructor(rollRoom: RollRoom) {
    this.rollRoom = rollRoom;
  }

  /** Take a day's readings in, which is to put them away in the roll room. */
  takeIn(day: string, readings: Reading[]): void {
    this.rollRoom.putAway(day, readings);
  }

  /** The cubic feet the works made on one day, over every meter read. */
  madeOn(day: string): number | null {
    const readings = this.rollRoom.readingsOn(day);
    if (readings === NOT_ROLLED) {
      return NOTHING_TAKEN;
    }
    return readings.reduce((made, reading) => made + reading.cubicFeet, 0);
  }

  /** Every meter read on one day, in the order it was read. */
  metersOn(day: string): string[] {
    const readings = this.rollRoom.readingsOn(day);
    if (readings === NOT_ROLLED) {
      return [];
    }
    return readings.map((reading) => reading.meter);
  }

  /** Every day the office has a roll for, earliest first. */
  days(): string[] {
    return this.rollRoom.days();
  }
}
