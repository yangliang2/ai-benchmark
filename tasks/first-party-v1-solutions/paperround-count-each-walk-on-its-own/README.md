# paper round

The newsagent's morning round, in the standard library alone.

- `houses.py` — a `House`, the order a walk takes the houses in, and how an
  address is written down
- `rounds.py` — `Round`, one walk out of the shop, and `Bag`, what is carried
  on it
- `tallying.py` — `Slate`, where the shop's counting is done, and `Bundle`,
  one street's papers tied together
- `newsagent.py` — `Newsagent`, which puts a morning's houses and its rounds
  together and makes up the list the counter is worked from

Every ask stands on its own. What the shop answers is worked out from the
houses it has and the walk it was asked about, and what it answered the time
before is over and done with.

Run the tests with `pytest`.
