/**
 * The counter the store is worked from: one command, and what it says back.
 *
 * `run` is the whole of it — it is handed the words somebody typed and the
 * root of the drawer, and gives back what to print and what to exit with. It
 * picks up nothing from the environment on its own, so a test can work the
 * counter over a drawer of its own making without anything of the machine's
 * getting in.
 *
 * Nothing here runs on import. The entry point below is guarded, because Node
 * 22 has no `import.meta.main` and this is the idiom the runtime does have.
 */

import { fileURLToPath } from "node:url";

import { written } from "./packets.ts";
import { NOT_IN_THE_STORE, Store } from "./store.ts";

/** One turn at the counter: what to print, and what to exit with. */
export type Said = { code: number; lines: string[] };

/** What the counter exits with when it did what it was asked. */
export const DONE = 0;

/** What it exits with when the store would not do what it was asked. */
export const REFUSED = 1;

/** What it exits with when it was asked something it does not know. */
export const NOT_ASKED = 2;

/** Where the drawer is when nobody has named one. */
export const HERE = ".";

/** The name of the setting that names the drawer. */
export const NAMES_THE_DRAWER = "SEEDBANK";

export function run(argv: string[], root: string): Said {
  const store = new Store(root);
  const [command, ...rest] = argv;
  if (command === "list" && rest.length === 0) {
    return { code: DONE, lines: store.names() };
  }
  if (command === "show" && rest.length === 1) {
    const packet = store.packetFor(rest[0]);
    if (packet === NOT_IN_THE_STORE) {
      return { code: REFUSED, lines: ["nothing of that name in the store"] };
    }
    return { code: DONE, lines: written(packet).trimEnd().split("\n") };
  }
  return {
    code: NOT_ASKED,
    lines: ["the counter was asked something it does not know"],
  };
}

function main(): void {
  const said = run(process.argv.slice(2), process.env[NAMES_THE_DRAWER] ?? HERE);
  for (const line of said.lines) {
    process.stdout.write(`${line}\n`);
  }
  process.exitCode = said.code;
}

// Node 22 has no `import.meta.main`, so the entry point is guarded the way the
// runtime allows: nothing here runs when this module is merely imported.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
