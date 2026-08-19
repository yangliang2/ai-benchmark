/**
 * What one run of the shelf comes to, bag by bag.
 *
 * `Tariff` is the scale the office charges by — so much a day for standing a
 * bag at all, and so much a day on top of that for every kilo it stood at.
 * `Charges` is one shelf read against one tariff: what is owed on a bag, and
 * what has been paid on it already.
 *
 * The office asks only for what it arrived at. Where nobody wrote a weight
 * down for a bag, there is nothing owed against that bag and nothing is made
 * up for it either: the office would sooner have the day run light than ask
 * a man at the counter for a figure nobody arrived at.
 */

import { Bag, NOT_WEIGHED, Shelf } from "./shelf.ts";

/** A charge of nothing: what a bag left and fetched the same day costs. */
export const NOTHING_OWED = 0;

/** What has been paid on a bag nobody has yet paid anything on. */
export const NOTHING_PAID = 0;

/** What the tariff hands back where there is no charge to be arrived at. */
export const CANNOT_SAY = null;

export class Tariff {
  readonly aDay: number;
  readonly aKilo: number;

  constructor(aDay: number, aKilo: number) {
    this.aDay = aDay;
    this.aKilo = aKilo;
  }

  /**
   * What one bag comes to under this tariff, and `CANNOT_SAY` where there is
   * nothing to arrive at a charge from: a ticket with nothing standing against
   * it, or a bag nobody wrote a weight down for.
   */
  forStay(bag: Bag | undefined): number | null {
    if (bag === undefined || bag.kilos === NOT_WEIGHED) {
      return CANNOT_SAY;
    }
    return (this.aDay + this.aKilo * bag.kilos) * bag.days;
  }
}

export class Charges {
  readonly shelf: Shelf;
  readonly tariff: Tariff;
  private readonly paid: Map<number, number>;

  constructor(shelf: Shelf, tariff: Tariff, paid?: Map<number, number>) {
    this.shelf = shelf;
    this.tariff = tariff;
    this.paid = new Map(paid ?? []);
  }

  /** The tickets this run has something standing against, as they came in. */
  ticketed(): number[] {
    return this.shelf.ticketed();
  }

  /** What is owed on one bag. */
  owedOn(ticket: number): number | null {
    return this.tariff.forStay(this.shelf.bagFor(ticket)) ?? NOTHING_OWED;
  }

  /** What has been paid on one bag, and nothing where nothing has been. */
  paidOn(ticket: number): number {
    return this.paid.get(ticket) ?? NOTHING_PAID;
  }

  /** What is still owing on one bag. */
  stillToPay(ticket: number): number | null {
    const owed = this.owedOn(ticket);
    return owed === CANNOT_SAY ? CANNOT_SAY : owed - this.paidOn(ticket);
  }
}
