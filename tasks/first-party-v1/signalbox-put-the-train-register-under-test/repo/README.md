# signalbox

The box's train register, in the standard library alone.

- `register.py` — `read_entry`, which reads one line of the register, and
  `work_the_register`, which works the whole book down from the top
- `tests/` — where the box's tests go. There are none yet: the register has
  been read by the man on duty since the box was built.

The register is the written record of the block section: every train offered
to the box, every train that took the section, and every train that gave it
back. One train in the section at a time, and the book kept in the order
things happened.

Run the tests with `pytest`.
