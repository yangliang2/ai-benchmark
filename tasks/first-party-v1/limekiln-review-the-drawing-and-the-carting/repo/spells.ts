/**
 * The spells the burners worked the kiln in.
 *
 * A spell is the stretch of dockets one burner drew before the next took the kiln
 * over: who had it, the hour he took it and the hour he gave it up. Nothing
 * in here knows what was drawn or what became of it — a spell is worked out
 * from the dockets as they were handed in, and from nothing else.
 */

import { Docket } from "./dockets.ts";

/** One spell: the stretch of dockets one burner drew. */
export interface Spell {
  readonly burner: string;
  readonly from: number;
  readonly to: number;
}

/**
 * The spells these dockets were drawn in, in the order they were handed in. A
 * spell ends where the next burner takes the kiln over, and the spell the day
 * ends in is a spell like any other.
 */
export function spellsIn(dockets: Docket[]): Spell[] {
  const spells: Spell[] = [];
  let burner: string | null = null;
  let from = 0;
  let to = 0;
  for (const docket of dockets) {
    if (docket.who !== burner) {
      if (burner !== null) {
        spells.push({ burner, from, to });
      }
      burner = docket.who;
      from = docket.hour;
    }
    to = docket.hour;
  }
  return spells;
}

/** How long a spell ran, counting the hour it began and the hour it ended. */
export function hoursIn(spell: Spell): number {
  return spell.to - spell.from + 1;
}

/** The burner who had the kiln at this hour, or nobody where none had it. */
export function whoHadIt(spells: Spell[], hour: number): string | null {
  for (const spell of spells) {
    if (spell.from <= hour && hour <= spell.to) {
      return spell.burner;
    }
  }
  return null;
}
