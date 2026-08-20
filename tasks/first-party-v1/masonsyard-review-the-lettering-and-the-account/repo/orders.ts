/**
 * The order book: what the yard has been asked to cut, in the order it was
 * asked for.
 *
 * An order is set down as it was taken and is never altered afterwards — the
 * mark of the stone it is for, whose it is, the words that were given, and the
 * week it is wanted by. What is done about an order afterwards, and what it
 * comes to, is nobody's business in here.
 */

export class Order {
  readonly mark: string;
  readonly who: string;
  readonly given: string;
  readonly week: number;

  constructor(mark: string, who: string, given: string, week: number) {
    this.mark = mark;
    this.who = who;
    this.given = given;
    this.week = week;
  }
}

export class Book {
  private readonly kept: Order[];

  constructor(kept: Order[] = []) {
    this.kept = [...kept];
  }

  /** Set an order down as it was taken. */
  take(order: Order): void {
    this.kept.push(order);
  }

  /** Every order the book holds, in the order it came. */
  orders(): Order[] {
    return [...this.kept];
  }

  /** How many orders the book holds. */
  count(): number {
    return this.kept.length;
  }

  /** Every order taken for this name, in the order it came. */
  forName(who: string): Order[] {
    return this.kept.filter((order) => order.who === who);
  }

  /** Every order wanted by this week or before it, in the order it came. */
  dueBy(week: number): Order[] {
    return this.kept.filter((order) => order.week <= week);
  }

  /**
   * Strike an order off. It is out of the book, and the book is the shorter
   * for it: what is left standing in it is what is still to cut.
   */
  strikeOff(mark: string): void {
    const at = this.kept.findIndex((order) => order.mark === mark);
    if (at >= 0) {
      delete this.kept[at];
    }
  }
}
