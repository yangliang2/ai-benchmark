# standrig

The rig that brings a hardware test stand's stations up and down. Everything
a run does to the stand is appended to a log, so a run can be read back
afterwards. Standard library only.

- `Station(name, log)` — one station, with `start()` and `stop()`.
- `stand(names, log)` — a station per name, in order, sharing one log.
- `still_up(log)` — what a run started and did not stop.
- `describe(log)` — a one-line summary of a run.

Run the tests with `pytest`.
