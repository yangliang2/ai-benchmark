/**
 * What the yard charges, and what a quarter of it comes to.
 *
 * A piece of work is a stone with words on it, and it is charged for twice
 * over: for the stone itself, by the inch, and for the lettering, by the
 * hundred. Everything in here is worked in pence, and only the foot of an
 * account is ever brought to shillings.
 */

import { lettersIn } from "./inscription.ts";
import { Stone } from "./stones.ts";

/** How many pence go to a shilling. */
export const PENCE_TO_A_SHILLING = 12;

/** How many letters the lettering rate is quoted by. */
export const LETTERS_TO_A_HUNDRED = 100;

export class Rate {
  readonly perInch: number;
  readonly perHundred: number;

  constructor(perInch: number, perHundred: number) {
    this.perInch = perInch;
    this.perHundred = perHundred;
  }

  /** What the stone itself comes to, in pence. */
  forStone(stone: Stone): number {
    return stone.inches * this.perInch;
  }

  /**
   * What the lettering comes to, in pence: by the hundred letters and figures
   * the words were given in, a part hundred not being charged for at all.
   */
  forLetters(given: string): number {
    return Math.floor(lettersIn(given) / LETTERS_TO_A_HUNDRED) * this.perHundred;
  }
}

export class Piece {
  readonly stone: Stone;
  readonly given: string;

  constructor(stone: Stone, given: string) {
    this.stone = stone;
    this.given = given;
  }
}

export class Account {
  private readonly rate: Rate;
  private readonly pieces: Piece[];

  constructor(rate: Rate, pieces: Piece[] = []) {
    this.rate = rate;
    this.pieces = [...pieces];
  }

  /** The account with one more piece of work set down on it. */
  setDown(piece: Piece): Account {
    return new Account(this.rate, [...this.pieces, piece]);
  }

  /** What each piece comes to, in pence, in the order it was set down. */
  lines(): number[] {
    return this.pieces.map(
      (piece) => this.rate.forStone(piece.stone) + this.rate.forLetters(piece.given),
    );
  }

  /** What the whole account comes to, in whole shillings. */
  comesTo(): number {
    return this.lines().reduce(
      (total, pence) => total + Math.floor(pence / PENCE_TO_A_SHILLING),
      0,
    );
  }
}
