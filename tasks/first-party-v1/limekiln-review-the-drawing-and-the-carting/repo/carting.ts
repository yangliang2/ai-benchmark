/**
 * The loads the carts take away, and the day sheet they are set down on.
 *
 * A load is one cart taking away what was drawn: the number painted on the
 * cart, how many bushels went on it, and the hour it was loaded. Nothing in
 * here knows which kiln the lime came out of or who drew it, and a sheet set
 * down on is a new sheet — the one it was set down on is left alone.
 */

export class Load {
  readonly cart: string;
  readonly bushels: number;
  readonly hour: number;

  constructor(cart: string, bushels: number, hour: number) {
    this.cart = cart;
    this.bushels = bushels;
    this.hour = hour;
  }
}

export class Sheet {
  private readonly made: Load[];

  constructor(made: Load[] = []) {
    this.made = [...made];
  }

  /** The sheet with one more load set down on it. */
  loaded(load: Load): Sheet {
    return new Sheet([...this.made, load]);
  }

  /** Every load set down, in the order it was made. */
  loads(): Load[] {
    return [...this.made];
  }

  /** Every cart that carried away, in the order it first loaded. */
  carts(): string[] {
    const seen: Record<string, boolean> = {};
    for (const load of this.made) {
      seen[load.cart] = true;
    }
    return Object.keys(seen);
  }

  /** What this cart carried away, in bushels; none where it never loaded. */
  carried(cart: string): number {
    return this.made
      .filter((load) => load.cart === cart)
      .reduce((total, load) => total + load.bushels, 0);
  }
}
