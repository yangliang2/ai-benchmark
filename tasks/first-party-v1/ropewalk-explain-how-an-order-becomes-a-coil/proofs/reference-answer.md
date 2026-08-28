# How an order becomes a coil

The question is the passage of one asking - fifty fathoms of hawser-laid
rope - from the counter to the dispatch book, and the code carries it in
four steps: counter.py decides what to walk, walk.py takes yarn off the
rack and lays it up, book.py tags and prices the result, and stores.py is
the file all of it is read from and saved back to. cli.py loads the yard
once, runs the one order, and saves once.

## What happens

The clerk runs `python cli.py order Trelawney 50 hawser`. cli.py loads the
yard file and hands the order to `counter.take_order`, which checks the lay
against the STRANDS table ("hawser" is there, worth 3 strands) and checks
the fathoms are at least one. Then the counter decides the length: the
counter rounds the asked fathoms up to a whole number of 20-fathom hauls
before anything is walked - `hauls_for(50)` is a ceiling division coming to
3 hauls, so the walk is given 60 fathoms, not 50.

`walk.walk_out` turns that length into a draw on the rack. The yarn needed
is the walked fathoms multiplied by the strand count of the lay -
`yarn_for(60, 3)` is 180 fathoms of yarn, one full run of the walk per
strand. Before anything moves, the whole 180 is checked against the rack's
total: `stores.on_hand` sums every bundle, and only if the total covers the
need does the walk call `stores.draw`. The draw takes bundles from the
front of the rack, in the order they were put up - the front bundle is
drawn empty before the next is touched, and a bundle drawn partway keeps
its place with what is left. The walk returns a coil record carrying the
60 fathoms, the lay, the 180 fathoms of yarn and the marks of the bundles
the draw touched.

`book.enter` finishes the passage. It takes a tag by reading the yard's
`next_serial` field and stepping it by one (`take_serial`), writes the tag
as "RW-" plus the number, and appends a dispatch entry holding the tag,
the customer, the asked 50, the walked 60, the lay, and the price. The
price is computed over the walked fathoms rather than the fathoms the
customer asked for: 60 fathoms at hawser's 9 pence a fathom is 540 pence,
though the asking was 50. cli.py prints the tag and saves the yard, so the
smaller rack, the stepped serial and the new entry all land in one write.

## Why it comes out that way

The load-bearing decisions, one by one:

- `counter.HAUL_FATHOMS` is 20 and `hauls_for` is a ceiling division
  (`-(-fathoms // HAUL_FATHOMS)`), so an asking is made up to the next
  whole haul and never cut down. Fifty fathoms is three hauls, sixty.
- `walk.yarn_for` is `fathoms * strands`: each strand runs the full walked
  length, and STRANDS says hawser lay is three strands.
- `walk.walk_out` compares `stores.on_hand(yard)` with the full need
  before it calls `draw` at all, so an order the rack cannot cover is
  refused whole and the rack is left exactly as it stood; nothing is drawn
  on the way to a refusal.
- `stores.draw` walks `yard["bundles"]` from index 0, popping each bundle
  it empties, so consumption is strictly front-of-rack first - the order
  `put_up` appended them, delivery order.
- `book.enter` computes `price_pence` as `coil["fathoms"] *
  PENCE_PER_FATHOM[lay]` - the walked length, not the asked one. The entry
  keeps both figures ("asked" and "walked") side by side, so the book
  itself shows the difference it charges across.

## Boundaries and edge behavior

An asking that is already a whole number of hauls (40, 60) is walked at
exactly its own length, and the two figures in the entry agree; the
round-up only shows when the asking does not come out even. An asking of
less than one fathom, or a lay the STRANDS table does not name, is refused
at the counter before the walk or the rack is touched. If the rack's total
cannot cover the yarn, the refusal happens in `walk_out` before any draw:
the yard is unchanged, no serial is taken, and nothing reaches the book -
there is no path in this code on which a short rack yields a shorter coil.
`stores.draw` itself guards against overdrawing, but on the order path
that guard is unreachable because `walk_out` has already checked the
total. `stores.load` invents an empty yard when the file is missing, so
the first order against a fresh yard is refused for want of yarn rather
than crashing.

What the repository alone cannot settle, named rather than papered over:
nothing in the code says what becomes of the ten surplus fathoms - whether
the customer keeps them or the yard cuts them off later, the book only
records that they were walked and charged. Nothing prices or returns
offcuts, and no path ever puts drawn yarn back on the rack. And the price
table and haul length are constants in the code, so what the yard would do
if a lay or a rate changed mid-book is outside what this code decides.
