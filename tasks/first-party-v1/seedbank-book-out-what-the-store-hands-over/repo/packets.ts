/**
 * A packet of seed, and the form one is written in on the card filed with it.
 *
 * A packet is what the store hands over: a name to ask for it by, the variety
 * it was gathered off, the year of the gathering, and how many seeds are in it
 * now. What is written on its card is four fields, one to a line, and reading
 * a card back is `readOff`'s business — it says outright when what it was
 * handed is not a card at all, because a card nobody can read is not a packet
 * of nought seeds.
 *
 * A packet is never written over in place. `holding` hands back the same
 * packet with a different number of seeds in it, which is what the store files
 * when seed has gone out of the drawer.
 */

/** What `readOff` gives back where what it was handed is not a card. */
export const NOT_A_PACKET = null;

/** One field of a card: `name: broad bean`, and nothing else on the line. */
const FIELD = /^([a-z]+): (.*)$/;

export class Packet {
  readonly name: string;
  readonly variety: string;
  readonly gathered: number;
  readonly seeds: number;

  constructor(name: string, variety: string, gathered: number, seeds: number) {
    this.name = name;
    this.variety = variety;
    this.gathered = gathered;
    this.seeds = seeds;
  }

  /** The same packet, with a different number of seeds in it. */
  holding(seeds: number): Packet {
    return new Packet(this.name, this.variety, this.gathered, seeds);
  }
}

/** What goes on the card filed with one packet. */
export function written(packet: Packet): string {
  return [
    `name: ${packet.name}`,
    `variety: ${packet.variety}`,
    `gathered: ${packet.gathered}`,
    `seeds: ${packet.seeds}`,
    "",
  ].join("\n");
}

/** The packet a card stands for, or not a packet where it cannot be read. */
export function readOff(card: string): Packet | null {
  const fields = new Map<string, string>();
  for (const line of card.split("\n")) {
    const found = FIELD.exec(line.trim());
    if (found !== null) {
      fields.set(found[1], found[2]);
    }
  }
  const name = fields.get("name");
  const variety = fields.get("variety");
  const gathered = Number(fields.get("gathered"));
  const seeds = Number(fields.get("seeds"));
  if (name === undefined || name === "" || variety === undefined) {
    return NOT_A_PACKET;
  }
  if (!Number.isInteger(gathered) || !Number.isInteger(seeds)) {
    return NOT_A_PACKET;
  }
  return new Packet(name, variety, gathered, seeds);
}
