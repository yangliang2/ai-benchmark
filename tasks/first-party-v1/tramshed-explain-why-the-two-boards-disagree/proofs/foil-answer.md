# Two boards, two hands: why the shed disagrees with itself

The tram shed's little repository is honest about its own history: one
board went up when the shed opened, the other two summers later, and
the pair of them were never quite made to march in step. The
disagreement over the 9:40 and the 10:05 is that history showing
through.

## What happens

The shed's record is chalked up end by end. The town men book their
workings as the cars are told off for the day, and the quay men book
theirs; the two boards disagree because they read different, separately
kept lists of workings - each board is fed from its own end's page of
the record, and nothing in the day's working ever reconciles the two
pages against each other.

The town board is the older and simpler of the two: it lists its cars
in the order the workings were entered into the book, on the principle
that the foreman chalks the day up as he plans it and the board should
read the way he chalked it. This morning the town foreman told off the
10:05 working before the 9:40 one - the long run to town gets its car
and crew settled first - so the 10:05 stands above the 9:40, exactly as
it went down.

The quay board, the newer one, was given a tidier habit when it went
up: it presents its page in running order for the men on the quay, so
its 9:40 car prints first and its 10:05 second, as the clock would have
it.

## Why it comes out that way

Nothing here is a fault in either board taken alone. Each is faithful
to its own page: the town board to the sequence of the foreman's
chalk, the quay board to the running of the day. What the shed never
built is the thing between them - a single shared record both boards
would have to agree with. Because the pages are kept apart and filled
in by different hands at different moments, the same pair of times can
arrive in a different sequence on each page, and the boards then
faithfully reproduce a disagreement that was really made at the
chalkboard, not in the code.

The cli bears this out: `town` and `quay` are two separate commands,
each going to its own board and its own end's workings, and there is no
command that prints one combined timetable - the shed has no single
view of the day for the two boards to be checked against.

## Boundaries and edge behavior

On a morning when the town foreman happens to chalk his workings in
clock order, the two boards agree, which is why the shed can go weeks
without noticing anything - the disagreement appears only when the
telling-off order and the clock order part company. Entering a working
with the `enter` command appends it to the end of its page, so a
latecomer chalked after the morning's planning lands at the bottom of
the town board whatever its time, while the quay board files it where
the day will actually run it. The `book` command shows the raw record,
pages in the order they were chalked. What the code cannot settle is
practice: whether the foreman ought to chalk in clock order, or the
town board ought to be given the quay board's tidier habit, is a
question for the shed, and the repository only preserves the two
habits as it found them.
