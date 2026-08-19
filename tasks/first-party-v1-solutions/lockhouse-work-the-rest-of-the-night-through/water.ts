/**
 * The cut, and what comes up it after dark.
 *
 * A `Boat` is one boat waiting at the gate: what it is called, what it is
 * carrying, and how deep it sits. How deep it sits is a number or it is
 * nothing at all, because the gauge board stands at the far end of the wharf
 * and not every boat is brought past it.
 *
 * A `Cut` is the water itself. Everything that happens on it reaches the
 * lockhouse as one of three things, and what tells them apart is how often
 * each happens: a boat comes up to the gate all evening, the pound is drawn
 * back to its mark every time the lock is worked, and the night shuts once.
 *
 * Nothing here happens the instant it is asked for. The paddles are drawn and
 * the pound comes up in its own time, so the water is given out when it has
 * come up and not before.
 */

import { EventEmitter } from "node:events";

/** How deep a boat sits, where nobody brought it past the gauge board. */
export const NOT_GAUGED = null;

/** A boat at the gate: what comes up the cut, all evening. */
export const A_BOAT = "boat";

/** The pound back at its mark: one drawing, and one every locking. */
export const WATER = "water";

/** The night shutting, which happens once and is not said twice. */
export const SHUTTING = "shutting";

export class Boat {
  readonly name: string;
  readonly tons: number;
  readonly deep: number | null;

  constructor(name: string, tons: number, deep: number | null = NOT_GAUGED) {
    this.name = name;
    this.tons = tons;
    this.deep = deep;
  }
}

export class Cut extends EventEmitter {
  /** A boat has come up to the gate. */
  aBoat(boat: Boat): void {
    this.emit(A_BOAT, boat);
  }

  /**
   * Draw the paddles. The pound is not up at the moment the paddles are
   * pulled: the water is given out when it stands at its mark, which is
   * afterwards, and whoever is waiting on it waits on that and not on a
   * length of time.
   */
  drawing(inches: number): void {
    queueMicrotask(() => {
      this.emit(WATER, inches);
    });
  }

  /** Nothing more is coming up tonight. */
  shutting(): void {
    this.emit(SHUTTING);
  }

  /** What is done when the night shuts, which is once and no more. */
  whenShutting(then: () => void): void {
    this.once(SHUTTING, then);
  }
}
