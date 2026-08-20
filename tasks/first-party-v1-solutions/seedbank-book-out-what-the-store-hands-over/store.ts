/**
 * The store itself: a drawer of cards, one to a packet, under one root.
 *
 * Everything the store knows is on disk. `names` reads the drawer, `packetFor`
 * reads one card back, and `file` writes one card out — making the drawer
 * first where nobody has made it yet. A name the drawer holds nothing under is
 * not in the store, which is not a packet of nought seeds.
 *
 * The store is told its root and never picks one: whoever built it says where
 * the drawer is, so nothing here writes anywhere the caller did not name.
 */

import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";

import { DAYBOOK, noted } from "./handouts.ts";
import { Packet, readOff, written } from "./packets.ts";

/** What the card filed with a packet is called after it. */
export const CARD = ".card";

/** What `packetFor` gives back for a name the drawer holds nothing under. */
export const NOT_IN_THE_STORE = null;

export class Store {
  readonly root: string;

  constructor(root: string) {
    this.root = root;
  }

  /** Where one packet's card is filed. */
  cardFor(name: string): string {
    return join(this.root, `${name}${CARD}`);
  }

  /** Every name the drawer holds a card under, in the order the drawer keeps
   * them, which is the order they read in. */
  names(): string[] {
    if (!existsSync(this.root)) {
      return [];
    }
    return readdirSync(this.root)
      .filter((entry) => entry.endsWith(CARD))
      .map((entry) => entry.slice(0, entry.length - CARD.length))
      .sort();
  }

  /** The packet filed under one name, or not in the store where none is. */
  packetFor(name: string): Packet | null {
    const card = this.cardFor(name);
    if (!existsSync(card)) {
      return NOT_IN_THE_STORE;
    }
    return readOff(readFileSync(card, "utf8"));
  }

  /** Write one packet's card out, over whatever was filed under that name. */
  file(packet: Packet): void {
    mkdirSync(this.root, { recursive: true });
    writeFileSync(this.cardFor(packet.name), written(packet), "utf8");
  }

  /** Where the day book is kept. */
  daybookAt(): string {
    return join(this.root, DAYBOOK);
  }

  /**
   * Hand that many seeds out of one packet, and write it down.
   *
   * The store refuses — and writes nothing at all — where it holds no packet
   * of that name, where the number asked for is not a whole number above
   * nought, or where the packet holds fewer seeds than that.
   */
  handOut(name: string, seeds: number): Packet {
    const packet = this.packetFor(name);
    if (packet === NOT_IN_THE_STORE) {
      throw new Error(`nothing of that name in the store: ${name}`);
    }
    if (!Number.isInteger(seeds) || seeds <= 0) {
      throw new Error(`that is not a number of seeds to hand out: ${seeds}`);
    }
    if (seeds > packet.seeds) {
      throw new Error(`only ${packet.seeds} seeds left of ${name}`);
    }
    const left = packet.holding(packet.seeds - seeds);
    this.file(left);
    appendFileSync(this.daybookAt(), `${noted(name, seeds, left.seeds)}\n`, "utf8");
    return left;
  }
}
