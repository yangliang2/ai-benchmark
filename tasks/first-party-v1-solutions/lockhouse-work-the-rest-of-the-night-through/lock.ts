/**
 * The lock itself, and the tally of what came up to it.
 *
 * Working a boat through is not something that happens at the moment it is
 * asked for. The paddles are drawn, the pound comes back to its mark in its
 * own time, and only then is the boat through. So `Lock.through` hands back a
 * promise that settles when the boat is out at the far end, and whoever
 * called it waits on that — never on a length of time, which on this cut is
 * a different number every night.
 *
 * One boat at a time. The chamber holds one, so the queue is kept by whoever
 * works the lock and not by the lock.
 */

import { A_BOAT, Boat, Cut, WATER } from "./water.ts";

/** How long the lock takes to work, before ever a boat is in it. */
export const A_LOCKING = 8;

export class Lock {
  readonly cut: Cut;
  readonly mark: number;
  private went = 0;
  private stood = 0;

  constructor(cut: Cut, mark: number) {
    this.cut = cut;
    this.mark = mark;
  }

  /**
   * Work one boat through, settling when it is out at the far end: the
   * paddles are drawn, the pound comes back up, and the boat goes through on
   * the water that came.
   */
  async through(boat: Boat): Promise<number> {
    this.stood = await this.drawn();
    this.went += 1;
    return A_LOCKING + boat.tons;
  }

  /** How many boats have been worked through tonight. */
  worked(): number {
    return this.went;
  }

  /** What the pound stood at when it was last drawn. */
  stands(): number {
    return this.stood;
  }

  /**
   * Wait for the pound to come back to its mark: the next drawing and no
   * more of them, because one drawing is one lockful and the one after it
   * belongs to the boat after this.
   */
  private drawn(): Promise<number> {
    const up = new Promise<number>((come) => {
      this.cut.once(WATER, come);
    });
    this.cut.drawing(this.mark);
    return up;
  }
}

/** What came up to the gate tonight, worked through or not. */
export class Tally {
  private came = 0;
  private shut = false;

  constructor(cut: Cut) {
    cut.on(A_BOAT, () => {
      this.came += 1;
    });
    cut.whenShutting(() => {
      this.shut = true;
    });
  }

  /** How many boats came up to the gate tonight. */
  boats(): number {
    return this.came;
  }

  /** Whether the night has shut. */
  shutUp(): boolean {
    return this.shut;
  }
}
