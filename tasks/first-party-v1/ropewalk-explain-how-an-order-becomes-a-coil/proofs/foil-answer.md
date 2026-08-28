# From the counter to the book: the passage of an order

The pleasant thing about this repository is how cleanly the trades of a
real ropewalk map onto its modules: an order is a conversation between the
counter, the walk, the rack and the book, and each module speaks only to
its neighbour. Tracing fifty fathoms of hawser through it is tracing that
conversation.

## What happens

The clerk types `python cli.py order Trelawney 50 hawser`. cli.py opens
the yard file - the single JSON record the whole yard lives in - and
passes the order to the counter. The counter is the yard's gatekeeper: it
looks the lay up, satisfies itself the order is well formed, and sends the
job down to the walk with the customer's measurements.

The walk is where rope actually gets made. It brings yarn down from the
rack - the rack is a running store of bundles, each delivery standing
under its own mark - and the walk helps itself as the work proceeds,
taking bundles down one by one as each runs out, the store keeping no more
ceremony about it than a real loft would. Hawser lay means strands
twisted against each other, so the walk consumes a good deal more yarn
than the rope it hands back, the twist eating the difference. The strands
are hooked, walked and closed, and the finished length is laid up into a
coil.

The coil then goes on the book. The book gives it a tag, records the
customer and the particulars of the order, and the dispatch entry is the
yard's receipt: the customer walks away with a tagged coil of the fifty
fathoms they asked for, and pays for the same - the entry prices the order
at the lay's rate over the length ordered. cli.py saves the yard file, and
the rack, the book and the serial are all one write further on.

## Why it comes out that way

The shape of the code is the shape of the trade. The counter validates
because the counter is where a customer can be told no cheaply, before any
yarn is committed. The walk owns the making because only the walk knows
what a lay costs in yarn; the rack is deliberately passive, a list the
walk draws against as it works. The book owns the tag and the price
because dispatch is the moment the yard commits to what it made: the entry
is written last, when there is a real coil to describe, which is why the
serial lives beside the dispatches in the yard file.

The pricing is the book's business and follows the order: the customer
asked for fifty fathoms at hawser's rate, and fifty fathoms at that rate
is what the entry charges. The modules never reach around each other -
cli.py talks to the counter, the counter to the walk, the walk to the
rack, and everything meets again only in the saved file.

## Boundaries and edge behavior

An unknown lay or a nonsense length is refused at the counter, before the
walk is troubled. The interesting edge is a thin rack: because the walk
draws as it goes, an order the rack cannot fully cover is walked short
from whatever yarn is there - the walk uses up the store and lays up what
it managed, and the book's entry shows the shortfall for the clerk to make
right when the next delivery comes. A missing yard file is treated as an
empty yard rather than an error, so a fresh yard's first commands work.
The bundles' marks are kept purely for the clerk's reading; nothing in the
code chooses between bundles by mark, age or size, so which bundle serves
which order is an accident of the store. What the code does not settle is
conduct between orders - there is no queue and no reservation, so two
orders arriving together are simply two runs of the program, and the file
written last wins.
