# A plan for hardening the maltings log

The pleasant thing about this repository is how narrow its front door is.
Every working the steward takes goes through one command-line file, and a
program with one door needs guarding in one place. Catching failures at the
command line — wrapping the steward's commands so no error escapes — is by
itself enough to meet the ruling: the modules below need no work of their
own, because nothing reaches them except through the commands, and a
command that cannot crash is a log that cannot be hurt.

## Pieces

**Piece 1 — the guard at the door.** Wrap the running of each command so
that any failure is caught, printed in the steward's own words, and the
program ends tidily. This is the change; the rest is housekeeping.

**Piece 2 — a morning look-over.** A small script the steward runs at the
start of the day that reads the log and prints how many lines it holds, so
a short file is noticed over the first mash rather than at month's end.

**Piece 3 — the paperwork.** Update the README so a new steward knows the
commands cannot crash and what the morning look-over is for, and have the
maltster minute the ruling as met before the season opens.

**Piece 4 — a season's shakedown.** Work the first fortnight of the season
normally and keep a tally of every message the guard prints, to show the
ruling holding in practice.

## Order and dependencies

The order is the numbering, and only loosely: the guard (Piece 1) is the
one piece that touches code and it blocks nothing else. The look-over, the
paperwork and the shakedown can be shared out and done in parallel in the
week before the season. There is no change to how the log is read or
written anywhere in this plan, and that is its strength: the file format
has served the house for years, and a plan that rebuilds the cellar to fix
a draught in the hall has mistaken where the weather gets in.

## Open questions and risks

The genuine risks are human rather than technical. The steward may come to
lean on the guard and stop reading its messages, so the wording of each
printed failure matters more than the machinery behind it. The maltster may
also want the guard's messages kept in a book of their own for the excise
man, which would be a small addition if asked for. Beyond that, the
repository takes this ruling in its stride: one guard at the one door,
standing from the right morning.
