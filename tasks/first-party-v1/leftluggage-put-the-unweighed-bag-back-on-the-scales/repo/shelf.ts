/**
 * The shelves the office keeps left luggage on.
 *
 * A `Bag` is one thing left over the counter: the ticket written out for it,
 * how many days it has stood there, what it stood at on the scales, and whose
 * name the office took. The scales are old and they are not always working, so
 * what a bag weighed is a number or it is nothing at all — and nothing at all
 * is not a bag that weighed nothing, which is not a bag anybody has ever left.
 *
 * What the shelf hands back where it has nothing to hand back says so: a
 * weight nobody wrote down comes back as not weighed, a bag the office took no
 * name for comes back as nobody, and a ticket with nothing standing against it
 * comes back as not on the shelf.
 */

/** What a bag weighed, where nobody wrote a weight down for it. */
export const NOT_WEIGHED = null;

/** Whose a bag is, where the office never took a name. */
export const NOBODY = null;

/** What the shelf hands back for a ticket it holds nothing against. */
export const NOT_ON_THE_SHELF = undefined;

export class Bag {
  readonly ticket: number;
  readonly days: number;
  readonly kilos: number | null;
  readonly holder: string | null;

  constructor(
    ticket: number,
    days: number,
    kilos: number | null = NOT_WEIGHED,
    holder: string | null = NOBODY,
  ) {
    this.ticket = ticket;
    this.days = days;
    this.kilos = kilos;
    this.holder = holder;
  }
}

export class Shelf {
  private readonly bags: Map<number, Bag>;

  constructor(bags: Bag[]) {
    this.bags = new Map(bags.map((bag) => [bag.ticket, bag]));
  }

  /** The tickets the office has something standing against, as they came in. */
  ticketed(): number[] {
    return [...this.bags.keys()];
  }

  /** What stands against one ticket, or not on the shelf where nothing does. */
  bagFor(ticket: number): Bag | undefined {
    return this.bags.get(ticket);
  }

  /** What one bag stood at, and not weighed where nobody wrote it down. */
  weighed(ticket: number): number | null {
    return this.bagFor(ticket)?.kilos ?? NOT_WEIGHED;
  }

  /** Whose one bag is, and nobody where the office took no name. */
  leftBy(ticket: number): string | null {
    return this.bagFor(ticket)?.holder ?? NOBODY;
  }
}
