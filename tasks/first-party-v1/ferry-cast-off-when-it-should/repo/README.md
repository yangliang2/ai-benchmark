# ferry

The village ferry, in the standard library alone.

- `passengers.py` — a `Passenger`, and `in_turn` for the order they are taken in
- `loading.py` — `Line`, which serves a waiting line one load at a time, and
  the reckoning a load is made up by
- `ferry.py` — `Ferry`, which puts the jetty and a boat of `BOAT_SEATS`
  together and says what the ferryman does next

A load is not worth moving until the line behind it is a whole load deep: a
line as long as a load takes, or longer, is served, and a shorter one holds
where it is until more join it.

Run the tests with `pytest`.
