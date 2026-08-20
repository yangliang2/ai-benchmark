/**
 * The table on the tollhouse wall: what the trust may charge, and for what.
 *
 * The table is the only place a figure is written down. It charges by the
 * axle, by the class of traffic the keeper writes on the pass, with a little
 * more for a load that is on rather than off. A class the table does not name
 * is not a free pass: it is traffic the trust has no figure for, and the
 * keeper is told so outright.
 */

/** What `tollFor` gives back for traffic the table does not name. */
export const NOT_ON_THE_TABLE = null;

/** Pence the axle, by class of traffic, as the table is written up. */
const THE_TABLE = new Map<string, number>([
  ["cart", 4],
  ["waggon", 6],
  ["gig", 3],
  ["drove", 2],
]);

/** Pence added where the load is on rather than off. */
export const LADEN = 2;

/** Every class of traffic the table names, in the order it is written up. */
export function classes(): string[] {
  return [...THE_TABLE.keys()];
}

/** What is owed on one pass, or not on the table where the trust has no figure. */
export function tollFor(traffic: string, axles: number, laden: boolean): number | null {
  const pence = THE_TABLE.get(traffic);
  if (pence === undefined || !Number.isInteger(axles) || axles < 1) {
    return NOT_ON_THE_TABLE;
  }
  return axles * pence + (laden ? LADEN : 0);
}
