/**
 * The dockets the burners hand in: what was drawn out of a kiln, in the order
 * they were handed in.
 *
 * A docket is set down as it was handed in and is never altered afterwards —
 * the mark of the kiln it came out of, the burner who drew it, what he wrote
 * in the place where the quantity goes, and the hour. What becomes of the
 * lime afterwards, and who carts it away, is nobody's business in here.
 */

export class Docket {
  readonly mark: string;
  readonly who: string;
  readonly written: string;
  readonly hour: number;

  constructor(mark: string, who: string, written: string, hour: number) {
    this.mark = mark;
    this.who = who;
    this.written = written;
    this.hour = hour;
  }

  /**
   * The bushels this docket is for, or nothing at all where what was written
   * in that place is not a plain figure.
   */
  asFigure(): number | null {
    const figure = Number.parseInt(this.written, 10);
    return Number.isNaN(figure) ? null : figure;
  }
}

export class DayBook {
  private readonly kept: Docket[];

  constructor(kept: Docket[] = []) {
    this.kept = [...kept];
  }

  /** Set a docket down as it was handed in. */
  take(docket: Docket): void {
    this.kept.push(docket);
  }

  /** Every docket handed in, in the order it came. */
  dockets(): Docket[] {
    return [...this.kept];
  }

  /** How many dockets were handed in. */
  count(): number {
    return this.kept.length;
  }

  /** Every docket this burner drew, in the order it came. */
  forBurner(who: string): Docket[] {
    return this.kept.filter((docket) => docket.who === who);
  }

  /**
   * What the day drew, in bushels: what the dockets carrying a figure come
   * to, a docket set aside adding nothing to the day.
   */
  drawn(): number {
    return this.kept.reduce((total, docket) => total + (docket.asFigure() ?? 0), 0);
  }
}
