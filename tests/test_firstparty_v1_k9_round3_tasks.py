"""K9's round-3 pairs, matched on write volume and betting on cost (#39).

Round 2 was the first rung separation any knob but K1 produced, and it came
with a confound its own verdict named: the two cruxes that moved a rung were
also the two whose reference solution wrote 40-60% more code than the control
beside it (1.61x and 1.41x added lines), and the pair that wrote *less* than
its control was the pair that stayed flat. "The crux is harder" and "the crux
is bigger" are not separated by that design, and the cost ordering the effort
instrument read off the same three pairs is collinear with the same line
counts. Until one round breaks the two apart, K9 is not usable as an ex-ante
profile dimension however good the rung result looks — which is what the
design note's section 18 verdict and section 23.3 ask round 3 for.

These pairs are that round. Each is authored so that the two reference
solutions add the same number of lines to the same module, within 10%, and
`test_the_pair_is_matched_on_how_much_there_is_to_write` holds them to it.
What is left between crux and control is the decision one of them withholds,
which is what K9 was always supposed to be measuring.

The second change is the metric. All eleven claims registered before round 3
are written on `turns`, and section 20 is why that stopped being good enough:
turn counts here are small integers, so a 1.25x turns claim is met by one
extra turn against a 4-turn comparator and needs two against an 8-turn one —
a stringency nobody registered. Every claim here is on `cost`, at the same
1.25x, and 1.25x is *not* fitted to round 2's measured cost multiples (2.65,
1.63, 1.17): registering the number those produce would be betting that a
mean of three reproduces, which is the mining this whole discipline exists to
avoid. The factor stays where round 2 put it and the metric moves.

The rung bets stay at the bottom of the ladder, and the rationale each task
registers says what would falsify them: with volume matched, a crux that
comes back sonnet-only anyway is the volume explanation of round 2's two
movements losing, not merely an author's bad luck.

Everything else is the round-2 design, deliberately unchanged so the two
rounds are readable against each other: two genuinely different resolutions
of each crux, asserted to return different answers and each graded 1.0; the
answer a reader reaches by never treating the open decision as one graded
0.0; a careless reading of a rule the crux *does* state graded 0.0 as well;
the control probed with the slip a careless reader of a fully stated spec
makes; and each crux arguing in its own task.yaml why recalling a named
method resolves nothing. The bookcase pair carries a second such careless
reading, `pack-the-shelves-without-the-dividers`, because there the careless
reading and the textbook method are the same program and the argument its
task.yaml makes is worth having run.

What "unchanged" covers is the vocabulary rather than the tests: the `Pair`,
`Probes` and `Bend` records, the mutation and answer-running helpers, the line
count and the task.yaml comment reader are all imported from the round-2
suite, because a second definition of a measurement is a second answer free to
disagree with the first. The tests themselves are written out again, which is
what this repo does with tests.

Section 23.3 of the design note carries a caveat this round is read under,
recorded there before any sweep: a named method fails a K9 grading suite only
where its output breaks a stated rule, and only one of these three pairs is
built that way.
"""

from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    TASKS,
    run_for,
    solution_diff,
    solved_tree,
    task_by_id,
    visible_tests_pass,
)
from test_firstparty_v1_k9_round2_tasks import PROBES as ROUND_TWO_PROBES
from test_firstparty_v1_k9_round2_tasks import (
    Bend,
    Pair,
    Probes,
    added_lines,
    answer_of,
    answering,
    authoring_comment,
)
from test_firstparty_v1_k9_tasks import PROBES as ROUND_ONE_PROBES

from ai_benchmark.firstparty_v1 import (
    EffortClaim,
    EffortMetric,
    Task,
    evaluate,
    lint_task_set,
    load_task_set,
)

# What every claim in this round is registered on, and the round's second
# change after volume matching. Pinned here rather than per pair because a
# round in which one pair quietly stayed on turns would be two experiments.
METRIC: EffortMetric = "cost"

# Unfitted, and the same number round 2 registered on turns. Round 2's cost
# multiples were 2.65x, 1.63x and 1.17x; registering any of those would be
# fitting the claim to the sweep that suggested it.
FACTOR = 1.25

# The widest a pair's two reference solutions may differ in added lines. Ten
# per cent is the design note's number (section 23.3), and it is a bound on
# the ratio either way round: the confound being broken is a difference in
# how much there was to write, whichever side wrote more.
VOLUME_TOLERANCE = 1.10


# --- the crux, resolved a second way -------------------------------------------

CLEAR_THE_LARGEST_DEBTS_FIRST = '''def pay(invoices, payment):
    """The ledger with `payment` applied, and the pence it could not be used
    for.

    The policy chosen: the largest debts first, so that the payment takes as
    much off the book as it can reach before the small invoices absorb it,
    and what the ledger is left holding is the cheapest of it to chase.
    """
    if payment != int(payment) or payment <= 0:
        raise ValueError(
            f"a payment of {payment} is not a whole number of pence to apply"
        )
    left = payment
    cleared = set()
    for position, invoice in sorted(
        enumerate(invoices), key=lambda entry: (-owing(entry[1]), entry[0])
    ):
        due = owing(invoice)
        if due and due <= left:
            left -= due
            cleared.add(position)
    return [
        invoice._replace(paid=invoice.amount) if position in cleared else invoice
        for position, invoice in enumerate(invoices)
    ], left
'''


CLOSE_A_SHELF_ONCE_IT_LOOKS_FULL = '''def shelve(books, width, divider):
    """The run laid out on shelves `width` millimetres wide.

    The policy chosen: close a shelf as soon as it is half full, so that the
    run comes out on shelves that all look deliberate rather than on a first
    shelf packed to the brim and a last one holding whatever was left.
    """
    shelves = []
    for stretch in runs(books):
        if span(stretch) > width:
            raise ValueError(
                f"the {stretch[0].subject} books take up {span(stretch)}mm, "
                f"which no {width}mm shelf holds"
            )
        standing = shelves[-1] if shelves else []
        taken = span(standing) + max(len(runs(standing)) - 1, 0) * divider
        if (
            not standing
            or taken * 2 >= width
            or taken + divider + span(stretch) > width
        ):
            shelves.append(list(stretch))
        else:
            standing.extend(stretch)
    return shelves
'''

KEEP_THE_MIDDLE_OF_THE_BURST = '''def pick(photos, pause):
    """One photograph from each burst of the roll.

    The policy chosen: the frame nearest the middle of what the burst leaves
    admissible. The first frames of a burst catch the subject arriving and the
    last catch it leaving, so the one in the middle is the likeliest of them
    to be the photograph that was wanted.
    """
    if not in_order(photos):
        raise ValueError("the roll does not run in time order")
    bursts = []
    for photo in photos:
        if bursts and photo.at - bursts[-1][-1].at <= pause:
            bursts[-1].append(photo)
        else:
            bursts.append([photo])
    kept = []
    for burst in bursts:
        wanted = marked(burst, "keep")
        if len(wanted) > 1:
            raise ValueError(f"{len(wanted)} photos of one burst are marked to keep")
        going = wanted or [p for p in burst if p.mark != "blurred"] or burst
        kept.append(going[(len(going) - 1) // 2])
    return kept
'''


# --- the answer arrived at by not making the decision ---------------------------

STOP_AT_THE_FIRST_ONE_YOU_CANNOT_AFFORD = '''def pay(invoices, payment):
    """The ledger with `payment` applied, and the pence left over.

    The payment goes down the ledger settling invoices as it meets them and
    stops at the first one it cannot afford, which is what the clerk does with
    a cheque and a spike of invoices.
    """
    if payment != int(payment) or payment <= 0:
        raise ValueError(
            f"a payment of {payment} is not a whole number of pence to apply"
        )
    left = payment
    cleared = set()
    for position, invoice in enumerate(invoices):
        due = owing(invoice)
        if due == 0:
            continue
        if due > left:
            break
        left -= due
        cleared.add(position)
    return [
        invoice._replace(paid=invoice.amount) if position in cleared else invoice
        for position, invoice in enumerate(invoices)
    ], left
'''


ONE_STRETCH_TO_A_SHELF = '''def shelve(books, width, divider):
    """The run laid out on shelves `width` millimetres wide: a shelf of its
    own for each stretch of one subject, so that nothing has to be settled
    about which stretches share and no divider is ever called for."""
    shelves = []
    for stretch in runs(books):
        if span(stretch) > width:
            raise ValueError(
                f"the {stretch[0].subject} books take up {span(stretch)}mm, "
                f"which no {width}mm shelf holds"
            )
        shelves.append(list(stretch))
    return shelves
'''

KEEP_THE_FIRST_FRAME_OF_EACH_BURST = '''def pick(photos, pause):
    """One photograph from each burst of the roll: the first of it, which is
    the frame the photographer took when they meant to."""
    if not in_order(photos):
        raise ValueError("the roll does not run in time order")
    bursts = []
    for photo in photos:
        if bursts and photo.at - bursts[-1][-1].at <= pause:
            bursts[-1].append(photo)
        else:
            bursts.append([photo])
    kept = []
    for burst in bursts:
        wanted = marked(burst, "keep")
        if len(wanted) > 1:
            raise ValueError(f"{len(wanted)} photos of one burst are marked to keep")
        kept.append(burst[0])
    return kept
'''


# --- the slip a careless reader of a rule the crux does state makes -------------

# The crux states that the office does not part-pay, and this reading applies
# the reference's policy and then puts what is left over on the next invoice
# still owing — which settles nothing and leaves an invoice sitting between
# untouched and settled, the one state the rule rules out.
PUT_THE_CHANGE_ON_THE_NEXT_INVOICE = '''def pay(invoices, payment):
    """The ledger with `payment` applied, and the pence it could not be used
    for.

    The reference's policy — the oldest debts first — with the change put
    towards the next invoice still owing rather than handed back.
    """
    if payment != int(payment) or payment <= 0:
        raise ValueError(
            f"a payment of {payment} is not a whole number of pence to apply"
        )
    left = payment
    applied = {}
    for position, invoice in enumerate(invoices):
        due = owing(invoice)
        if due and due <= left:
            left -= due
            applied[position] = invoice.amount
    for position, invoice in enumerate(invoices):
        if left and position not in applied and owing(invoice):
            applied[position] = invoice.paid + left
            left = 0
    return [
        invoice._replace(paid=applied[position]) if position in applied else invoice
        for position, invoice in enumerate(invoices)
    ], left
'''


# The crux refuses a *stretch* of one subject wider than a shelf, which is not
# the same bar as a book wider than one: three narrow books of one subject can
# come to more than any shelf holds while no single one of them does. This
# reading applies the bar to each book, so a stretch nothing can hold is laid
# out rather than refused.
READ_THE_BAR_AS_ONE_BOOK_WIDE = '''def shelve(books, width, divider):
    """The run laid out on shelves `width` millimetres wide.

    The reference's policy — fill each shelf as far as it goes — with the
    refusal read as a book wider than a shelf rather than a stretch wider than
    one.
    """
    shelves = []
    for stretch in runs(books):
        for book in stretch:
            if book.width > width:
                raise ValueError(
                    f"{book.title} is {book.width}mm, wider than a {width}mm shelf"
                )
        shelf = shelves[-1] if shelves else []
        if shelf and span(shelf) + len(runs(shelf)) * divider + span(stretch) <= width:
            shelf.extend(stretch)
        else:
            shelves.append(list(stretch))
    return shelves
'''

# And the crux's other stated rule, which is the one the textbook answer walks
# into: a shelf holds its books *and* a divider for every stretch on it after
# the first, so the sizes bin packing takes to add up do not. This is next fit
# over the stretches, the method a solver who names the shape is handed, and
# it overfills a shelf whose books alone came to less than the width.
PACK_THE_SHELVES_WITHOUT_THE_DIVIDERS = '''def shelve(books, width, divider):
    """The run laid out on shelves `width` millimetres wide: bin packing over
    the stretches, next fit, each shelf taking whole stretches until the one
    after will not fit on it and the next shelf started there."""
    shelves = []
    for stretch in runs(books):
        if span(stretch) > width:
            raise ValueError(
                f"the {stretch[0].subject} books take up {span(stretch)}mm, "
                f"which no {width}mm shelf holds"
            )
        if shelves and span(shelves[-1]) + span(stretch) <= width:
            shelves[-1].extend(stretch)
        else:
            shelves.append(list(stretch))
    return shelves
'''

# The crux states that a burst holds photographs taken no *more* than `pause`
# seconds apart, and this reading cuts at a gap of exactly the pause instead
# of holding it together — which splits a burst the roll does not.
CUT_THE_BURST_AT_A_GAP_OF_THE_PAUSE = '''def pick(photos, pause):
    """One photograph from each burst of the roll.

    The reference's policy — the last frame of the burst that may be kept —
    with a gap of exactly the pause read as the end of a burst.
    """
    if not in_order(photos):
        raise ValueError("the roll does not run in time order")
    bursts = []
    for photo in photos:
        if bursts and photo.at - bursts[-1][-1].at < pause:
            bursts[-1].append(photo)
        else:
            bursts.append([photo])
    kept = []
    for burst in bursts:
        wanted = marked(burst, "keep")
        if len(wanted) > 1:
            raise ValueError(f"{len(wanted)} photos of one burst are marked to keep")
        sharp = [photo for photo in burst if photo.mark != "blurred"]
        kept.append((wanted or sharp or burst)[-1])
    return kept
'''


# --- the slips a careless reader of a fully stated spec makes --------------------

# The control states that an invoice of exactly its terms is not late yet: it
# falls due that day and is chased from the day after. This reading chases it
# on the day it falls due.
CHASE_IT_THE_DAY_IT_FALLS_DUE = '''def overdue(invoices, today, terms):
    """The chase list for `today`: what is late, by how many days, and for how
    much."""
    if terms < 0:
        raise ValueError(
            f"terms of {terms} days are not terms an invoice can be granted"
        )
    chase = []
    for invoice in invoices:
        if today < invoice.raised:
            raise ValueError(
                f"{invoice.reference} was raised on day {invoice.raised}, "
                f"which is after the day {today} it is being chased on"
            )
        late = today - invoice.raised - terms
        if late >= 0 and not settled(invoice):
            chase.append((invoice.reference, late, owing(invoice)))
    return sorted(chase, key=lambda entry: (-entry[1], entry[0]))
'''


# The control states that a title shelved twice under one subject is listed
# once and that the width counts what is listed, so the copy passed over adds
# nothing. This reading lists the title once and counts the copy's width.
COUNT_THE_COPY_THAT_WAS_PASSED_OVER = '''def index(books):
    """The printed index: one (subject, titles, width) triple per subject."""
    listed = {}
    for book in books:
        if not book.subject:
            raise ValueError(f"{book.title} is filed under no subject at all")
        listed.setdefault(book.subject, []).append(book)
    return [
        (subject, list(dict.fromkeys(titles(under))), span(under))
        for subject, under in sorted(listed.items())
    ]
'''

# The control states that a photograph taken on a window's opening second
# belongs to that window rather than to the one before it. This reading counts
# it in both.
COUNT_A_PHOTO_ON_THE_BOUNDARY_TWICE = '''def windows(photos, every):
    """How many photographs fall in each window of `every` seconds."""
    if every <= 0:
        raise ValueError(f"a window of {every} seconds is no window at all")
    if not in_order(photos):
        raise ValueError("the roll does not run in time order")
    if not photos:
        return []
    counted = []
    opens = photos[0].at
    while opens <= photos[-1].at:
        counted.append(
            sum(1 for photo in photos if opens <= photo.at <= opens + every)
        )
        opens += every
    return counted
'''


# --- what each resolution actually answers, run for real ------------------------

# Printed from inside a solution tree, on the case each pair's two resolutions
# were built to come apart on.
PAID = """
from remit import Invoice, describe, pay

ledger = [
    Invoice("C-1", 2, 200, 0),
    Invoice("C-2", 5, 300, 0),
    Invoice("C-3", 8, 250, 0),
]
invoices, returned = pay(ledger, 300)
print(describe(invoices), returned)
"""

SHELVED = """
from bookcase import Book, describe, shelve

run = [
    Book("Moss", "plants", 20),
    Book("Ferns", "fungi", 20),
    Book("Lichen", "rocks", 20),
    Book("Slate", "roofs", 20),
]
print(describe(shelve(run, 100, 10)))
"""

PICKED = """
from roll import Photo, pick, shown

roll = [
    Photo(0, "heron-a", ""),
    Photo(1, "heron-b", ""),
    Photo(2, "heron-c", ""),
    Photo(40, "reeds", ""),
]
print(shown(pick(roll, 2)))
"""


PROBES: dict[str, Probes] = {
    "remit": Probes(
        module="remit.py",
        crux_definition="def pay(",
        control_definition="def overdue(",
        rung="haiku-solvable",
        at_least_factor=FACTOR,
        another_way=CLEAR_THE_LARGEST_DEBTS_FIRST,
        not_an_answer=STOP_AT_THE_FIRST_ONE_YOU_CANNOT_AFFORD,
        careless=(Bend("chase-it-the-day-it-falls-due", CHASE_IT_THE_DAY_IT_FALLS_DUE),),
        answers=PAID,
        misread=(
            Bend(
                "put-the-change-on-the-next-invoice",
                PUT_THE_CHANGE_ON_THE_NEXT_INVOICE,
            ),
        ),
    ),
    "bookcase": Probes(
        module="bookcase.py",
        crux_definition="def shelve(",
        control_definition="def index(",
        rung="haiku-solvable",
        at_least_factor=FACTOR,
        another_way=CLOSE_A_SHELF_ONCE_IT_LOOKS_FULL,
        not_an_answer=ONE_STRETCH_TO_A_SHELF,
        careless=(
            Bend(
                "count-the-copy-that-was-passed-over",
                COUNT_THE_COPY_THAT_WAS_PASSED_OVER,
            ),
        ),
        answers=SHELVED,
        misread=(
            Bend("read-the-bar-as-one-book-wide", READ_THE_BAR_AS_ONE_BOOK_WIDE),
            Bend(
                "pack-the-shelves-without-the-dividers",
                PACK_THE_SHELVES_WITHOUT_THE_DIVIDERS,
            ),
        ),
    ),
    "roll": Probes(
        module="roll.py",
        crux_definition="def pick(",
        control_definition="def windows(",
        rung="haiku-solvable",
        at_least_factor=FACTOR,
        another_way=KEEP_THE_MIDDLE_OF_THE_BURST,
        not_an_answer=KEEP_THE_FIRST_FRAME_OF_EACH_BURST,
        careless=(
            Bend(
                "count-a-photo-on-the-boundary-twice",
                COUNT_A_PHOTO_ON_THE_BOUNDARY_TWICE,
            ),
        ),
        answers=PICKED,
        misread=(
            Bend(
                "cut-the-burst-at-a-gap-of-the-pause",
                CUT_THE_BURST_AT_A_GAP_OF_THE_PAUSE,
            ),
        ),
    ),
}


def _pairs() -> tuple[Pair, ...]:
    """The pairs this suite probes, assembled from what each side knows.

    The task set says which tasks a pair id groups and which of them plants
    the crux — that is what its K9 level means — so nothing but the probes
    themselves is named here.
    """
    grouped: dict[str, dict[str, str]] = {}
    for task in load_task_set(TASKS):
        construction = task.construction
        if construction is None or construction.pair is None:
            continue
        grouped.setdefault(construction.pair, {})[
            construction.levels.get("K9", "")
        ] = task.id

    pairs = []
    for pair, probes in sorted(PROBES.items()):
        members = grouped.get(pair, {})
        assert set(members) == {"none", "single"}, (
            f"pair {pair!r} is not one K9 crux task and one control: {members}"
        )
        pairs.append(Pair(members["single"], members["none"], probes))
    return tuple(pairs)


PAIRS = _pairs()

BY_PAIR = [pytest.param(pair, id=pair.crux_id) for pair in PAIRS]

BY_BEND = [
    pytest.param(pair, bend, id=f"{pair.control_id}-{bend.name}")
    for pair in PAIRS
    for bend in pair.probes.careless
]

BY_MISREADING = [
    pytest.param(pair, bend, id=f"{pair.crux_id}-{bend.name}")
    for pair in PAIRS
    for bend in pair.probes.misread
]

TASK_IDS = tuple(
    task_id for pair in PAIRS for task_id in (pair.crux_id, pair.control_id)
)

BY_TASK = [pytest.param(task_id, id=task_id) for task_id in TASK_IDS]


def tasks() -> list[Task]:
    return [task_by_id(task_id) for task_id in TASK_IDS]


def declared(task: Task) -> dict[str, str]:
    assert task.construction is not None
    return task.construction.levels


# --- pairs differing in crux depth, and now in nothing else ---------------------


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_crux_task_plants_one_and_its_control_plants_none(pair: Pair) -> None:
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    assert declared(crux) == {"K9": "single"}
    assert declared(control) == {"K9": "none"}
    for task in (crux, control):
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"
        # Standalone tasks, not a family: a family holds repo/ byte-identical
        # and varies the prompt, and these two ask for different functions.
        assert task.construction is not None
        assert task.construction.family is None
        # What does group them, and what this suite reads the pairing off.
        assert task.construction.pair in PROBES


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_pair_starts_from_the_same_repository(pair: Pair) -> None:
    """What makes the control a control: same terrain, same matrix cell, so a
    difference in outcome is a difference in what was asked, not in where it
    was asked. The pair lint checks it across the whole task set; it is
    checked here too, against these tasks directly."""
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    def tree(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }

    assert tree(crux.repo_dir) == tree(control.repo_dir)


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_two_prompts_ask_for_different_things(pair: Pair) -> None:
    """The other half of what the pair holds constant. Everything in the
    repository is identical between the two, so the prompt is the whole of
    what moved, and two members sharing one would be a pair with no contrast
    in it at all."""
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    assert crux.prompt != control.prompt


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_pair_is_matched_on_how_much_there_is_to_write(pair: Pair) -> None:
    """The round's own claim, and the reason these tasks exist.

    Round 2's separation is confounded with write volume: its two cruxes that
    moved a rung added 1.61x and 1.41x the lines of the controls beside them,
    and the one that added fewer lines than its control is the one that stayed
    flat, so the ordering of the result is the ordering of the confound. Round
    2's own check was a factor of two either way, which those numbers pass.
    Here the two reference solutions add the same number of lines to the same
    module within 10%, so that whatever the sweep reads off this pair, "the
    crux was bigger" is not available as the reading.

    Asserted rather than recorded, because the match is a property of two
    files that are edited independently and would drift the first time either
    reference solution was rewritten.
    """
    crux = added_lines(task_by_id(pair.crux_id))
    control = added_lines(task_by_id(pair.control_id))

    assert crux and control
    assert max(crux, control) / min(crux, control) <= VOLUME_TOLERANCE, (
        f"{pair.crux_id} adds {crux} lines against {pair.control_id}'s {control}"
    )


def test_every_k9_pair_in_the_task_set_is_probed_by_one_of_the_suites() -> None:
    """K9 is probed by three suites now, and nothing else says the three cover
    it between them.

    A pair's probes are the part no metadata carries, and adding a pair to the
    task set is a change to a directory rather than to any suite — so an
    unprobed pair would sweep looking exactly like a probed one, its crux
    never shown to accept a second answer or refuse a non-answer. Registering
    one pair in two suites is the other way for the cover to be wrong, and
    reads as agreement while one of the two goes stale.

    This lives in the newest suite because it is the only one that can see
    every registry: round 2's holds the same assertion over two rounds, and
    keeping it there as well would take a third registry it cannot import
    without a cycle, or a second copy of the answer free to disagree.
    """
    declared_pairs = {
        task.construction.pair
        for task in load_task_set(TASKS)
        if task.construction is not None
        and task.construction.pair is not None
        and "K9" in task.construction.levels
    }
    registries = (ROUND_ONE_PROBES, ROUND_TWO_PROBES, PROBES)

    for one, other in ((0, 1), (0, 2), (1, 2)):
        assert not set(registries[one]) & set(registries[other])
    assert declared_pairs == set().union(*(set(probes) for probes in registries))


def test_the_tasks_lint_clean() -> None:
    """Linted on their own, which these can be: every effort claim registered
    here is read against a pair partner that is in this same set, so no rule
    the lint applies asks about tasks outside it."""
    assert lint_task_set(tasks()) == []


@pytest.mark.parametrize("task_id", BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    task_id: str,
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("task_id", BY_TASK)
def test_the_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert len(touched) == 1
    assert task.scale == "single-file"


@pytest.mark.parametrize("task_id", BY_TASK)
def test_the_repository_starts_out_green_and_stays_green(task_id: str) -> None:
    """The net the agent inherits passes, and goes on passing once the change
    is made: a K9 crux withholds a decision, never a warning, so nothing the
    agent can run is misleading about the work it has already done."""
    task = task_by_id(task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


# --- the planted crux: several answers, and grading that accepts them -----------


@pytest.mark.parametrize("pair", BY_PAIR)
def test_a_second_resolution_of_the_crux_also_resolves(pair: Pair) -> None:
    """The K9 probe, and the one that decides whether the knob is what it says.

    A suite that accepted only the reference's policy would make the task a
    spec whose decision was made and never written down — unsolvable except by
    guessing the author — so a second, differently reasoned answer to the same
    open decision has to grade 1.0.
    """
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task,
        mutate=answering(
            pair.probes.module, pair.probes.crux_definition, pair.probes.another_way
        ),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_two_resolutions_really_do_answer_differently(pair: Pair) -> None:
    """And the guard on the probe above. Two policies that happen to return
    the same thing would prove nothing about the grading suite's tolerance:
    what has to be shown is that it accepts two different answers, so both are
    run and their answers compared."""
    task = task_by_id(pair.crux_id)

    reference = answer_of(task, pair.probes.answers, None)
    another = answer_of(
        task,
        pair.probes.answers,
        answering(
            pair.probes.module, pair.probes.crux_definition, pair.probes.another_way
        ),
    )

    assert reference.strip() and reference != another


@pytest.mark.parametrize("pair", BY_PAIR)
def test_not_making_the_decision_does_not_resolve(pair: Pair) -> None:
    """The other direction, and what keeps the tolerance above from being
    indifference: the answer a reader arrives at by never treating the open
    decision as one satisfies everything about the change except the rule the
    decision exists to meet.

    What each probe pins, since the three are not equally on the nose. Remit's
    walks the ledger settling invoices until one it cannot afford and stops,
    which leaves change that would have settled a later invoice — the
    maximality rule, and the only rule the withheld policy answers to.
    Bookcase's gives every stretch a shelf of its own, which is what "decide
    nothing about which stretches share" comes to, and it trips the half-full
    floor — again the rule the open decision lives under. Roll's keeps the
    first frame of every burst without reading the marks, and what it trips is
    the keep mark and the blurred rule, two stated rules, rather than anything
    about which admissible frame survives: roll withholds a decision no rule
    constrains at all, so there is no rule left for a non-answer to fail, and
    this probe is a second misreading wearing the label rather than a third of
    a kind. That is the same asymmetry §23.3 records for the round.
    """
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task,
        mutate=answering(
            pair.probes.module, pair.probes.crux_definition, pair.probes.not_an_answer
        ),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize(("pair", "bend"), BY_MISREADING)
def test_a_careless_reading_of_the_crux_does_not_resolve(
    pair: Pair, bend: Bend
) -> None:
    """The crux tasks state rules too, and everything a crux states outright
    its grading suite has to hold it to. A suite that let a stated rule through
    would be a suite tolerating more than the one decision the task leaves
    open, and the tolerance the K9 probes above demonstrate would be that much
    less evidence that what the crux withholds is a decision rather than a
    reading."""
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task,
        mutate=answering(pair.probes.module, pair.probes.crux_definition, bend.answer),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize(("pair", "bend"), BY_BEND)
def test_a_careless_reading_of_the_control_does_not_resolve(
    pair: Pair, bend: Bend
) -> None:
    """Nothing left to invent is not nothing left to get wrong: each control
    is probed with the slip a reader who skimmed one stated rule would make,
    so a control that graded anything would not be a control at all."""
    task = task_by_id(pair.control_id)
    diff = solution_diff(
        task,
        mutate=answering(
            pair.probes.module, pair.probes.control_definition, bend.answer
        ),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_are_the_k9_round_three_claim() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.

    All of them sit at the bottom of the ladder, which is round 2's own
    calibration lesson (its sixteen bottom-rung bets went fourteen for
    sixteen) and not an author's modesty. It is also the reading these pairs
    were built to test: round 2's two rung movements arrived on cruxes writing
    half as much code again as their controls, so a matched pair coming back
    flat is what the volume explanation predicts. A crux that reaches
    sonnet-only here with the volume held level costs this prediction and
    settles the question the other way, which is the trade the round is for.
    """
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {
        task_id: pair.probes.rung
        for pair in PAIRS
        for task_id in (pair.crux_id, pair.control_id)
    }
    assert set(registered.values()) == {"haiku-solvable"}


def test_the_registered_effort_claims_are_on_cost_at_the_unfitted_factor() -> None:
    """What these pairs actually bet, and the half a sweep can take off them.

    Against the pair partner rather than the baseline, because a partner is a
    version-matched within-round contrast and the frozen baseline is the
    weakest comparator this experiment has. On cost rather than turns, which
    is the round's second change: turns quantize at these counts, so an
    identical factor is a different bet against a cheap comparator than
    against an expensive one, and cost accumulates the reading and retrying
    that happen inside a turn.

    The factor is round 2's, unchanged and deliberately not fitted to what
    round 2 measured on cost (2.65x, 1.63x, 1.17x). A claim set to the number
    a previous sweep produced is a description of that sweep; 1.25x is a bet
    that survives being wrong.
    """
    registered = {
        task.id: task.construction.prediction.effort
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {
        task_id: claim
        for pair in PAIRS
        for task_id, claim in (
            (
                pair.crux_id,
                EffortClaim(
                    comparator="pair",
                    metric=METRIC,
                    at_least_factor=pair.probes.at_least_factor,
                ),
            ),
            (pair.control_id, None),
        )
    }
    assert {claim.at_least_factor for claim in registered.values() if claim} == {FACTOR}


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_effort_claim_is_held_by_the_member_with_the_crux_in_it(
    pair: Pair,
) -> None:
    """A direction guard, so that a claim registered on the wrong member reads
    as the contradiction it is rather than as the theory quietly running the
    other way. A pair comparator is symmetric — either member could name the
    other — and a control claiming to cost more than the crux beside it would
    be K9 registered upside down."""
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    assert crux.construction is not None and control.construction is not None
    claim = crux.construction.prediction.effort
    assert claim is not None and claim.at_least_factor > 1.0
    assert control.construction.prediction.effort is None


@pytest.mark.parametrize("task_id", BY_TASK)
def test_every_prediction_names_the_decision_it_turns_on(task_id: str) -> None:
    """A rationale is what a missed prediction teaches, and for K9 what it has
    to teach is which decision was expected to be the hard one — for a crux
    task the one left open, for a control the fact that none is."""
    task = task_by_id(task_id)

    assert task.construction is not None
    rationale = task.construction.prediction.rationale
    assert len(rationale.split()) >= 15
    assert any(word in rationale for word in ("open", "stated", "decision"))


@pytest.mark.parametrize("pair", BY_PAIR)
def test_every_crux_argues_why_recalling_an_algorithm_would_not_resolve_it(
    pair: Pair,
) -> None:
    """The requirement round 2 introduced and round 3 keeps, held to where an
    author would otherwise be trusted for it.

    Round 1's three cruxes were bin packing, rearrange-k-apart and debt
    simplification, so the decision each withheld was one a solver could be
    handed by recognising the shape, and the round could not tell invention
    from recall. A crux registered here has to make the case in its own
    task.yaml that no named algorithm resolves it — which the sweep cannot
    check and a reader of the task alone would have to take on trust.

    What this holds a crux to is making the argument, not to the argument
    coming out one particular way, and §23.3 records why the difference
    matters: only `bookcase-shelve-the-run` reaches the strong form, where the
    named method's answer breaks a stated rule. The other two make the honest
    weaker case in their own comments, that the method lands inside the family
    of answers the rules accept and nothing asked for it.
    """
    comment = authoring_comment(pair.crux_id)

    assert "recall" in comment
    assert "textbook" in comment
    assert len(comment.split()) >= 80


@pytest.mark.parametrize("pair", BY_PAIR)
def test_every_crux_records_that_its_pair_was_matched_on_volume(pair: Pair) -> None:
    """The confound this round removes, argued where the task is read rather
    than only where it is tested. A reader meeting one of these tasks on its
    own has no way to see that the control beside it was written to the same
    length on purpose, and that is the fact that separates a round-3 pair from
    a round-2 one.

    Two words rather than one, because "volume" on its own is met by a comment
    that happens to use the word: the pair has to be said to have been matched
    on it.
    """
    comment = authoring_comment(pair.crux_id)

    assert "volume" in comment
    assert "matched" in comment
