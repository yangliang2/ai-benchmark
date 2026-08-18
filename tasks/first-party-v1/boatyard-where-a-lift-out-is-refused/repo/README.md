# The boatyard

A small yard that hauls boats out of the water for the winter and puts them
back in the spring.

- `slipway.py` — the crane at the head of the slipway, and the book of tides
  that says which days it can lift on.
- `cradles.py` — the store of frames a hull rests on once it is ashore, and
  which of them would take a hull of a given width.
- `yard.py` — the standings the yard has, and what the office says to somebody
  who telephones and asks to be hauled out.

The two narrow modules settle one thing each and decide nothing on their own;
the yard is where their verdicts meet the standings, the tides and the season
somebody has asked for.

Run the tests with `pytest`. Nothing outside the standard library is needed.
