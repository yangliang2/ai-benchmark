/**
 * The lockhouse: the standing orders it works to, and the night it keeps.
 *
 * `Orders` is what the lockhouse may let through — the deepest a boat may sit
 * and clear the sill. A boat nobody gauged is not let through on a guess.
 *
 * `Keeper` is one night. A boat handed in goes behind whatever stands in the
 * chamber already: the chamber holds one, so what comes up the cut queues,
 * works through in the sequence it arrived, and is entered on the page as it
 * clears the far end. A boat arriving on top of another has lost nothing by
 * it — the chamber holds one of them and the night holds all of them — and
 * nothing is finished until the queue is empty.
 *
 * The promise the night hands back settles on the work being finished and
 * never on a length of time: the cut shut, and the queue empty.
 */

import { fileURLToPath } from "node:url";

import { Book, turnedBack, writtenUp } from "./book.ts";
import { Lock, Tally } from "./lock.ts";
import { A_BOAT, Boat, Cut, NOT_GAUGED, SHUTTING, WATER } from "./water.ts";

export class Orders {
  readonly deepest: number;

  constructor(deepest: number) {
    this.deepest = deepest;
  }

  /** Whether the lockhouse may let this boat through at all. */
  willTake(boat: Boat): boolean {
    return boat.deep !== NOT_GAUGED && boat.deep <= this.deepest;
  }
}

export class Keeper {
  readonly cut: Cut;
  readonly lock: Lock;
  readonly book: Book;
  readonly orders: Orders;
  private working: Promise<void> = Promise.resolve();
  private lockfuls = 0;

  constructor(cut: Cut, lock: Lock, book: Book, orders: Orders) {
    this.cut = cut;
    this.lock = lock;
    this.book = book;
    this.orders = orders;
  }

  /**
   * Keep one night, and settle when the night's work is finished: what comes
   * back is the page as it stands then.
   */
  async keep(): Promise<string[]> {
    this.cut.once(A_BOAT, (boat: Boat) => {
      this.take(boat);
    });
    this.cut.on(WATER, () => {
      this.lockfuls += 1;
    });
    await new Promise<void>((shut) => {
      this.cut.once(SHUTTING, shut);
    });
    await this.working;
    return this.book.read();
  }

  /** How many lockfuls of water the night took. */
  drew(): number {
    return this.lockfuls;
  }

  /** Put one boat behind whatever is in the chamber already. */
  private take(boat: Boat): void {
    this.working = this.working.then(() => this.workThrough(boat));
  }

  /** One boat: through and entered, or turned back and entered. */
  private async workThrough(boat: Boat): Promise<void> {
    if (!this.orders.willTake(boat)) {
      this.book.write(turnedBack(boat));
      return;
    }
    this.book.write(writtenUp(boat, await this.lock.through(boat)));
  }
}

async function main(): Promise<void> {
  const cut = new Cut();
  const book = new Book();
  const tally = new Tally(cut);
  const keeper = new Keeper(cut, new Lock(cut, 30), book, new Orders(9));
  book.headed(cut);
  book.marked(cut);

  const night = keeper.keep();
  for (const boat of [
    new Boat("Sally", 20, 8),
    new Boat("Kingfisher", 14, 6),
    new Boat("Bittern", 30, 12),
  ]) {
    cut.aBoat(boat);
  }
  cut.shutting();

  console.log((await night).join("\n"));
  console.log(`${tally.boats()} boats, ${keeper.drew()} lockfuls`);
}

// Node 22 has no `import.meta.main`, so the entry point is guarded the way the
// runtime allows: nothing here runs when this module is merely imported.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  void main();
}
