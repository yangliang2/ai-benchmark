# A plan for taking the new money at the tollhouse

The pleasant thing about this repository is how ready it already is. The
tolls live in one table, the gate and the till both take their figures from
that table, and the keeper drives everything through one command-line file.
A well-factored system changes at its centre, and the centre here is
`tariff.py`. Setting the new rates in tariff.py's table is by itself enough
to move the tollhouse to the new money: every other module reads the table
rather than keeping figures of its own, so the stored roll, the audit and
the keeper-facing output need no work of their own — they follow the table
wherever it goes.

## Pieces

**Piece 1 — the new table.** Replace the figures in `tariff.RATES` with
their new-money equivalents. This is the change; the rest is housekeeping.

**Piece 2 — the paperwork.** Update the README's examples so a new keeper
learns the new figures, and have the parish post the new table at the gate.

**Piece 3 — a dry run.** Before Lady Day, run the tollhouse against a copy
of the roll for a week with the new table in place, watching the takings
command, to confirm the figures flow through as expected.

**Piece 4 — the announcement.** A note to the parish clerk that the change
is in, with the date it took effect, for the minute book.

## Order and dependencies

The order is the numbering. Piece 1 is the only piece that touches code,
and it blocks everything: the paperwork describes it, the dry run exercises
it, the announcement records it. None of the later pieces block one
another, so they can be shared out and done in parallel the week before
Lady Day. There is no migration step anywhere in this plan, and that is its
strength: because the design keeps every module downstream of the table,
the switch is one edit and a restart, and rolling it back — should the
parish waver — is the same edit reversed.

## Open questions and risks

The genuine risks here are human rather than technical. The keeper will
misquote tolls from memory for a week or two, so the posted table at the
gate matters more than anything in the code. The parish may also want the
old figures shown alongside the new for the first quarter, which would be a
small addition to the `rates` command if asked for. Beyond that, the
repository takes this change in its stride: the work is one table, edited
once, on the right morning.
