/**
 * The stones standing in the yard, and how one is asked for.
 *
 * A stone is what the mason has to work with before anybody has asked for
 * anything to be cut on it: what it is made of, how big it is, and the mark
 * chalked on its foot while it stands out there. Nothing in here knows what is
 * to go on a stone, who asked for it, or what it will be charged at.
 *
 * A mark is matched however it was chalked, because whoever rough-hews a stone
 * chalks it, and the yard has never once agreed about capitals.
 */

/** What the yard works in. */
export const KINDS = ["slate", "limestone", "granite"];

export class Stone {
  readonly mark: string;
  readonly kind: string;
  readonly inches: number;

  constructor(mark: string, kind: string, inches: number) {
    this.mark = mark;
    this.kind = kind;
    this.inches = inches;
  }
}

export class Yard {
  private readonly rough: Stone[];

  constructor(rough: Stone[] = []) {
    this.rough = [...rough];
  }

  /** Every stone out there, in the order it was rough-hewn. */
  stones(): Stone[] {
    return [...this.rough];
  }

  /** How many stones are standing. */
  count(): number {
    return this.rough.length;
  }

  /** The yard with one more stone standing in it. */
  hewn(stone: Stone): Yard {
    return new Yard([...this.rough, stone]);
  }
}

/** The stone this mark stands for, however it was chalked, or nothing at all. */
export function standing(yard: Yard, mark: string): Stone | null {
  const wanted = mark.trim().toLowerCase();
  for (const stone of yard.stones()) {
    if (stone.mark.trim().toLowerCase() === wanted) {
      return stone;
    }
  }
  return null;
}
