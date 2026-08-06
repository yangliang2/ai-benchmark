# outage

Reading a run of faults as time a service was down, standard library only.

- `Fault(name, start, end)` — one fault, in minutes, covering `start` up to
  but not including `end`.
- `stretch(fault)` — the minutes one fault covers.
- `spans(faults)` — the stretches of downtime the faults add up to, with
  overlapping faults put together.
- `downtime(faults)` — how many minutes at least one fault was covering.
- `covering(faults, minute)` — who was covering a given minute.
- `describe(faults)` — a printable summary of the downtime.

Run the tests with `pytest`.
