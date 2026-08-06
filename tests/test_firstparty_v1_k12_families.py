"""The K12 decision-conveyance families (ticket #32): two underlying changes,
each authored as four variants of how one withheld decision reaches the
solver.

K12's ladder is the only one in the registry whose *order* is the claim
rather than a vocabulary. It was derived from round 1's failing diffs and
written into the design note before any of this existed: stating the decision
as an acceptance criterion is easiest, pointing at the repository primitive
that already enforces it is next, saying nothing and leaving the module to be
read is next, and describing the decision's shape in prose is worst — below
saying nothing — because prose displaces the module as the source of truth
and steers the implementation shape. So the tests below pin the ladder as a
sequence and guard its direction, and a family that came back in the other
order would be the falsification these tasks exist to allow.

What a family holds constant, and how K1 can be part of it. Everything but
the prompt is byte-identical across the four variants, which the task-set
lint enforces and the per-family lint run below carries. The prompt is where
a spec-side knob moves, and here it moves in exactly one place: the four
prompts share one block of acceptance criteria verbatim, and each variant
inserts a single passage carrying the crux — the `unmentioned` variant
inserting nothing at all, so its prompt *is* the shared block. That is what
makes K1 honestly constant at `acceptance` across a family whose whole point
is that one decision is withheld from three of its members: where K12 is
declared, K1 is read over the spec's other decisions and K12 scopes the crux
out of it (design note section 9). `test_only_the_crux_passage_varies_across
_the_prompts` is that reading made checkable rather than asserted in a
comment: it takes the four prompts apart and shows there is one place they
differ.

The two families' prose variants are deliberately not written alike. The
album family's says only what shape the change has and points nowhere;
the pricelist family's closes with "whatever the module already makes of one
rule against another, `price_for` should make of them too", which is the
sentence round 1's `settings-l2` carried and lost with. So one family tests
bare prose and the other tests prose that *also* sends the reader back to the
module — which matters, because the second conveys strictly more than its
`unmentioned` sibling does and is still predicted to be the harder of the
two. A ladder where prose only looked hard because it said less would explain
itself away; this one cannot.

Their `repo-primitive` variants are not equal in strength either, and that is
worth recording before a sweep reads them as one level. Album's pointer sends
the solver to the reader that answers which keywords an album carries, and
that reader *is* the crux: whoever follows the pointer has thereby decided
that two keywords canonicalising alike are one keyword, and lands on 1.0.
Pricelist's sends the solver to the ranking `describe_rules` is written on,
and the ranking is half of its crux: it settles which rule outranks which and
says nothing about a sale being priced by one rule and one only, so an answer
that follows the pointer literally and still lets every rule that speaks take
its cut grades 0.0. Both are registered at the same rung, because the level is
the same act — pointing at a primitive that already enforces the decision —
but the two pointers hand over different fractions of what was withheld, and
reconciliation should read a pricelist `repo-primitive` miss as the weaker
pointer before reading it as the level failing.

Every variant is solvable from the repository alone, including the two that
say nothing useful about the crux, because a variant whose decision cannot be
recovered is unsolvable by construction rather than hard. What shows it is
`test_an_answer_written_differently_but_correctly_still_resolves`: the answer
it grades is composed out of the module's own readers and takes nothing from
any prompt, and it grades 1.0 against every variant's held-out suite.

The predictions are registered in two pieces, and deliberately not the same
piece for every level:

- The **rung** carries the ladder claim. Three levels sit at the bottom, which
  is round 1's calibration lesson applied — 0 for 12 on "this knob makes it
  harder" outside K1 — and `prose` is bet one rung up, which is that lesson's
  own exception for a specific mechanism: `settings-merge-layers-l2` is a
  prose-conveyance variant that came back `unsolved` on both models while its
  siblings were solved, and both failing diffs transcribed the prose.
- The **effort claim** carries reading burden, which is *not* the ladder.
  Round 1 measured prose as the cheap answer, not the dear one: settings-l2
  took haiku 5 turns against l1's 7 and l3's 9, and failed both models where
  l3 was solved. Prose was the cheap answer and the wrong one; saying nothing
  cost more and got solved. So each family declares two pairs —
  criterion against repo-primitive, and prose against unmentioned — and the
  effort claim in each is held by the member with more of the repository to
  read, betting turns against its partner. The two levels that read the least
  register no claim at all, which claims nothing rather than claiming the
  knob is free.

Each half has its own direction guard — one refusing a rung ladder that runs
backwards, the other refusing an effort claim held by the member with less to
read. Between them a factor or a rung mistyped into the wrong variant reads
as the contradiction it is rather than as the theory quietly running the
other way.
"""

from collections.abc import Callable
from os.path import commonprefix
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import (
    SOLUTIONS,
    run_for,
    solution_diff,
    solved_tree,
    task_by_id,
    visible_tests_pass,
)

from ai_benchmark.firstparty_v1 import (
    KNOB_LEVELS,
    EffortClaim,
    Rung,
    Task,
    evaluate,
    lint_task_set,
)

# The K12 ladder, easiest conveyance first. A family's variants are named for
# their place on it: <stem>-c1 is written at LADDER[0], and so on. Read from
# the registry rather than written out again, because the registry is already
# pinned against the design note where it belongs — beside the other ladders,
# in test_firstparty_v1.py — and a second copy here could only disagree with
# it. What this suite adds is that the tasks are laid along it in order.
LADDER = KNOB_LEVELS["K12"]

# How much of the repository each level makes the solver read, least first.
# Deliberately not the ladder: prose is the hardest level and the second
# cheapest, because it hands over a shape to transcribe instead of a module to
# consult. The effort claims are registered along this order, the rungs along
# the ladder, and the two disagreeing about prose is the finding.
READING = ("criterion", "repo-primitive", "prose", "unmentioned")

# The operational difficulty ladder, easiest rung first, so that predictions
# can be compared as well as pinned.
RUNGS: tuple[Rung, ...] = ("haiku-solvable", "sonnet-only", "unsolved")

# The level whose prompt is the shared block and nothing else.
SHARED_ONLY = "unmentioned"


# --- the careless answers: what transcribing the prose arrives at --------------

# Two keywords are compared as they were typed. It canonicalises the answer,
# because every variant asks for that in as many words — and then never asks
# the module what makes two keywords one keyword. This is also what the prose
# variant's passage transcribes to: "appears in the second album's own list of
# keywords" is the as-written reader, so what following that sentence arrives
# at is checked in here rather than left to be argued about after a sweep.
MATCH_THE_KEYWORDS_AS_TYPED = '''def shared_keywords(one, other):
    """The keywords both albums carry, canonically, in alphabetical order."""
    return sorted({
        canonical(keyword)
        for keyword in keywords(one)
        if keyword in keywords(other)
    })
'''

# Farther out, and the answer somebody writes once the first has been pointed
# out to them: one side is canonicalised and the other still is not, so it
# matches whenever the second album happened to type the keyword canonically
# and misses whenever it did not.
CANONICALISE_ONE_SIDE_ONLY = '''def shared_keywords(one, other):
    """The keywords both albums carry, canonically, in alphabetical order."""
    return sorted({
        canonical(keyword)
        for keyword in keywords(one)
        if canonical(keyword) in keywords(other)
    })
'''

# Every rule that speaks gets its say, one after another: "letting them settle
# the price between them" spelled the way it reads. Right whenever one rule
# speaks, which is most sales.
LET_EVERY_RULE_THAT_SPEAKS_HAVE_ITS_SAY = '''def price_for(price_list, sku, quantity):
    """What a customer pays for `quantity` of `sku`."""
    amount = list_price(price_list, sku) * quantity
    for rule in price_list.rules:
        if speaks_to(rule, sku, quantity):
            amount = discounted(amount, rule.percent_off)
    return amount
'''

# Farther out: one rule decides, which is the module's own arrangement, but
# the one that decides is the one written last rather than the one that
# outranks the others. Wrong only when the price list is written in the order
# that disagrees with the ranking.
LET_THE_LAST_RULE_WRITTEN_DECIDE = '''def price_for(price_list, sku, quantity):
    """What a customer pays for `quantity` of `sku`."""
    amount = list_price(price_list, sku) * quantity
    winner = None
    for rule in price_list.rules:
        if speaks_to(rule, sku, quantity):
            winner = rule
    if winner is None:
        return amount
    return discounted(amount, winner.percent_off)
'''


# --- the honest variants: the same contract, composed from the module ----------

# Both take everything they know from the module and nothing from any prompt,
# which is what makes them the discoverability probe as well as the over-fit
# one: an answer written by a reader who had only the repository resolves.

ASK_THE_MODULE_WHAT_EACH_ALBUM_CARRIES = '''def shared_keywords(one, other):
    """The keywords both albums carry, canonically, in alphabetical order."""
    shared = []
    for keyword in sorted(keyword_set(one)):
        if has_keyword(other, keyword):
            shared.append(keyword)
    return shared
'''

KEEP_THE_HIGHEST_RANKED_RULE_AS_YOU_GO = '''def price_for(price_list, sku, quantity):
    """What a customer pays for `quantity` of `sku`."""
    amount = list_price(price_list, sku) * quantity
    winner = None
    for rule in price_list.rules:
        if speaks_to(rule, sku, quantity) and (
            winner is None or rank(rule) > rank(winner)
        ):
            winner = rule
    return amount if winner is None else discounted(amount, winner.percent_off)
'''


class Bend(NamedTuple):
    """One careless answer, under the name a probe failure reports it by."""

    name: str
    answer: str


class Family(NamedTuple):
    """One K12 family, and everything pinned about it here.

    `module` is the single file the reference solution edits and `definition`
    is where the added function starts, which is what lets a probe swap one
    answer for another — the added function is the last thing in its module,
    as an agent's diff would leave it. `rungs`, `effort` and `pairs` are the
    pre-registration, keyed by K12 level; a level absent from `effort`
    registers no effort claim, which registers nothing rather than claiming
    the level is free.
    """

    stem: str
    module: str
    definition: str
    rungs: dict[str, Rung]
    effort: dict[str, EffortClaim]
    pairs: dict[str, str]
    careless: tuple[Bend, ...]
    differently: str


def turns_against_the_partner(at_least_factor: float) -> EffortClaim:
    return EffortClaim(
        comparator="pair", metric="turns", at_least_factor=at_least_factor
    )


FAMILIES = (
    Family(
        stem="album-shared-keywords",
        module="album.py",
        definition="def shared_keywords(",
        rungs={
            "criterion": "haiku-solvable",
            "repo-primitive": "haiku-solvable",
            "unmentioned": "haiku-solvable",
            "prose": "sonnet-only",
        },
        effort={
            "repo-primitive": turns_against_the_partner(1.1),
            "unmentioned": turns_against_the_partner(1.2),
        },
        pairs={
            "criterion": "album-shared-keywords-stated",
            "repo-primitive": "album-shared-keywords-stated",
            "unmentioned": "album-shared-keywords-withheld",
            "prose": "album-shared-keywords-withheld",
        },
        careless=(
            Bend("match-the-keywords-as-typed", MATCH_THE_KEYWORDS_AS_TYPED),
            Bend("canonicalise-one-side-only", CANONICALISE_ONE_SIDE_ONLY),
        ),
        differently=ASK_THE_MODULE_WHAT_EACH_ALBUM_CARRIES,
    ),
    Family(
        stem="pricelist-price-a-sale",
        module="pricelist.py",
        definition="def price_for(",
        rungs={
            "criterion": "haiku-solvable",
            "repo-primitive": "haiku-solvable",
            "unmentioned": "haiku-solvable",
            "prose": "sonnet-only",
        },
        effort={
            "repo-primitive": turns_against_the_partner(1.1),
            "unmentioned": turns_against_the_partner(1.2),
        },
        pairs={
            "criterion": "pricelist-price-a-sale-stated",
            "repo-primitive": "pricelist-price-a-sale-stated",
            "unmentioned": "pricelist-price-a-sale-withheld",
            "prose": "pricelist-price-a-sale-withheld",
        },
        careless=(
            Bend(
                "let-every-rule-that-speaks-have-its-say",
                LET_EVERY_RULE_THAT_SPEAKS_HAVE_ITS_SAY,
            ),
            Bend("let-the-last-rule-written-decide", LET_THE_LAST_RULE_WRITTEN_DECIDE),
        ),
        differently=KEEP_THE_HIGHEST_RANKED_RULE_AS_YOU_GO,
    ),
)

BY_FAMILY = [pytest.param(family, id=family.stem) for family in FAMILIES]

BY_VARIANT = [
    pytest.param(family, f"{family.stem}-c{index}", id=f"{family.stem}-c{index}")
    for family in FAMILIES
    for index in (1, 2, 3, 4)
]

BY_BEND = [
    pytest.param(family, f"{family.stem}-c{index}", bend,
                 id=f"{family.stem}-c{index}-{bend.name}")
    for family in FAMILIES
    for index in (1, 2, 3, 4)
    for bend in family.careless
]


def variants(family: Family) -> list[Task]:
    """The family's four task directories, in ladder order."""
    return [task_by_id(f"{family.stem}-c{index}") for index in (1, 2, 3, 4)]


def tree(root: Path) -> dict[str, str]:
    """Every file under root, by relative path, for comparing whole trees."""
    return {
        str(path.relative_to(root)): path.read_text()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def declared(task: Task) -> dict[str, str]:
    assert task.construction is not None
    return task.construction.levels


def answering(family: Family, answer: str) -> Callable[[Path], None]:
    """Replace the reference solution's added function with another answer."""

    def edit(workdir: Path) -> None:
        source = workdir / family.module
        head, marker, _ = source.read_text().partition(family.definition)
        assert marker, f"{family.module} has no {family.definition}"
        source.write_text(head + answer, encoding="utf-8")

    return edit


class Prompts(NamedTuple):
    """The four prompts taken apart into the block they share and the passage
    each one inserts into it, keyed by K12 level."""

    shared_before: str
    shared_after: str
    passages: dict[str, str]


def taken_apart(family: Family) -> Prompts:
    """The four prompts split into what they share and what each one adds.

    Derived rather than pinned: the shared block is the longest common prefix
    and suffix of the four prompts, and what is left between them is the
    passage the crux travels in. Deriving it is the point — a prompt edited so
    two variants no longer share their acceptance criteria shrinks the common
    part, and the difference surfaces here as a passage nobody wrote.
    """
    by_level = {declared(task)["K12"]: task.prompt for task in variants(family)}
    prompts = [by_level[level] for level in LADDER]
    before = commonprefix(prompts)
    remainders = [prompt[len(before):] for prompt in prompts]
    after = commonprefix([remainder[::-1] for remainder in remainders])[::-1]
    return Prompts(
        before,
        after,
        {
            level: remainder[: len(remainder) - len(after)]
            for level, remainder in zip(LADDER, remainders, strict=True)
        },
    )


# --- each family is one change conveyed four ways -------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_family_is_four_variants_of_one_conveyance_ladder(
    family: Family,
) -> None:
    """The K12 levels run in ladder order across -c1 to -c4, and K1 is the
    same level in all four: the spec's other decisions are written as
    acceptance criteria everywhere, so the only thing moving is how the crux
    reaches the solver."""
    tasks = variants(family)

    assert len(tasks) == 4
    assert [declared(task)["K12"] for task in tasks] == list(LADDER)
    for task in tasks:
        assert task.construction is not None
        assert task.construction.family == family.stem
        assert set(declared(task)) == {"K1", "K12"}
        assert declared(task)["K1"] == "acceptance"
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_two_pairs_are_the_two_contrasts_the_claim_is_read_on(
    family: Family,
) -> None:
    """A family is four variants; a pair is two of them read against each
    other, which is what an effort claim can be settled against. The stated
    half is criterion against repo-primitive and the withheld half is
    unmentioned against prose — the contrast the ladder's whole claim is
    about, since prose sitting below unmentioned is the part round 1 found and
    the part a sweep can take off us."""
    declared_pairs = {
        declared(task)["K12"]: task.construction.pair
        for task in variants(family)
        if task.construction is not None
    }

    assert declared_pairs == family.pairs
    assert len(set(family.pairs.values())) == 2
    assert family.pairs["unmentioned"] == family.pairs["prose"]
    assert family.pairs["criterion"] == family.pairs["repo-primitive"]


@pytest.mark.parametrize("family", BY_FAMILY)
def test_every_variant_ships_the_same_reference_solution(family: Family) -> None:
    """Self-contained copies rather than shared directories, so no run can be
    shaped by another variant — but identical copies, or the family would be
    varying the diff target as well as the conveyance. The repo/ and grading/
    halves are the task-set lint's job (below); the reference solutions sit
    outside the task directories, where the lint cannot see them."""
    [first, *rest] = variants(family)

    for task in rest:
        assert tree(SOLUTIONS / task.id) == tree(SOLUTIONS / first.id)


@pytest.mark.parametrize("family", BY_FAMILY)
def test_only_the_crux_passage_varies_across_the_prompts(family: Family) -> None:
    """The isolation this family rests on, and the reading of K1 that lets it
    declare one level in all four members.

    The four prompts share a block verbatim — the change, its signature, and
    every decision but the crux, written as acceptance criteria — and each
    variant inserts one passage into it. The `unmentioned` variant inserts
    nothing, so the shared block is exactly its whole prompt: there is no
    sense in which it is a *shorter* spec than its siblings, only one in which
    three of them say something more about the one decision K12 is about.
    """
    before, after, passages = taken_apart(family)
    by_level = {declared(task)["K12"]: task.prompt for task in variants(family)}

    for level in LADDER:
        assert by_level[level] == before + passages[level] + after

    assert passages[SHARED_ONLY] == ""
    shared = before + after
    assert shared == by_level[SHARED_ONLY]
    # Read with the line wrapping taken out: which line a criterion breaks on
    # is not what is being asserted about it.
    unwrapped = " ".join(shared.split())
    assert "It must satisfy all of the following:" in unwrapped
    assert "Keep the existing functions and their behaviour unchanged" in unwrapped

    inserted = [passages[level] for level in LADDER if level != SHARED_ONLY]
    assert all(passage.strip() for passage in inserted)
    assert len(set(inserted)) == len(inserted)


# --- every variant is a well-formed, solvable task ------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_family_lints_clean_as_a_whole(family: Family) -> None:
    """Which covers the family invariants — one knob varied, each of its
    levels used once, byte-identical starting repositories and grading suites,
    prompts that actually differ — and the pair invariants too, since both
    pairs are wholly inside the family. Nothing here needs the rest of the
    task set: both effort claims are read against a pair partner, not against
    a category baseline."""
    assert lint_task_set(variants(family)) == []


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    family: Family, task_id: str
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_the_declared_scale_matches_the_reference_solution(
    family: Family, task_id: str
) -> None:
    """`single-file` is pinned across the family further up; what is left is
    that the reference solution is in fact one file, and which one."""
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {family.module}


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_the_repository_starts_out_green(family: Family, task_id: str) -> None:
    """K12 withholds a decision, never a warning: the net the agent inherits
    passes before the change and goes on passing after it."""
    task = task_by_id(task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


# --- what the conveyance buys, and what it costs --------------------------------


@pytest.mark.parametrize("family, task_id, bend", BY_BEND)
def test_a_careless_answer_passes_the_visible_suite_and_still_grades_unresolved(
    family: Family, task_id: str, bend: Bend
) -> None:
    """The answer transcribing the prose arrives at, graded against every
    variant — the grading suites are byte-identical, so what this shows is
    that no variant's held-out suite lets it through, including the one whose
    prompt described the shape it came from.

    Nothing the agent can run says it is wrong. The repository's own tests
    pass: they passed before the change and the change did not touch what they
    cover. Only the held-out suite exercises two keywords typed two ways, or a
    sale two rules speak to at once, and it grades the answer 0.0.
    """
    task = task_by_id(task_id)
    careless = answering(family, bend.answer)

    assert visible_tests_pass(task, solved_tree(task, careless))

    [record] = evaluate(
        [task], [run_for(task, solution_diff(task, mutate=careless))], source="run-log"
    )

    assert record.quality_value == 0.0


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_an_answer_written_differently_but_correctly_still_resolves(
    family: Family, task_id: str
) -> None:
    """Two things at once, and the second is the one K12 needs.

    The ordinary one: an answer reaching the same contract by another route —
    asking the module about each keyword in turn instead of intersecting two
    sets, keeping the best rule as it goes instead of taking a maximum — must
    grade 1.0, or the held-out suite is describing the reference solution's
    shape rather than the contract.

    The one this knob rests on: neither answer takes anything from any prompt.
    Both are composed out of the module's own readers, which is what a solver
    who had only the repository would write — so a variant that says nothing
    about the crux, and a variant that describes it misleadingly, are both
    solvable from the repository alone. A variant whose decision could not be
    recovered that way would be unsolvable by construction rather than hard,
    and would measure nothing about conveyance.
    """
    task = task_by_id(task_id)
    diff = solution_diff(task, mutate=answering(family, family.differently))

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


# --- pre-registered predictions -------------------------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_registered_rungs_are_the_familys_k12_claim(family: Family) -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.

    Three levels at the bottom of the ladder, which is round 1's calibration
    lesson applied rather than authorial modesty: outside K1 the record on
    "this knob makes it harder" was 0 for 12. `prose` is bet one rung up
    because it has the mechanism that lesson makes the exception for —
    `settings-merge-layers-l2` is a prose-conveyance variant that came back
    unsolved on both models while both its siblings were solved.
    """
    registered = {
        declared(task)["K12"]: task.construction.prediction.rung
        for task in variants(family)
        if task.construction is not None
    }

    assert registered == family.rungs


@pytest.mark.parametrize("family", BY_FAMILY)
def test_no_family_predicts_that_prose_is_easier_than_saying_nothing(
    family: Family,
) -> None:
    """The ladder-direction guard on the rungs, and the whole of what K12
    registers. Pinning each family's rungs says what that family claims; this
    says what no K12 family may claim, so a rung mistyped into another variant
    reads as the contradiction it is rather than as the ladder quietly running
    backwards. It bites hardest at the last step: prose sits below unmentioned
    because prose displaces the module, and a family predicting otherwise
    would be denying the finding it was built from."""
    predicted = [RUNGS.index(family.rungs[level]) for level in LADDER]

    assert predicted == sorted(predicted)
    assert RUNGS.index(family.rungs["prose"]) >= RUNGS.index(
        family.rungs["unmentioned"]
    )


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_registered_effort_claims_are_the_reading_burden_bet(
    family: Family,
) -> None:
    """What these families bet on price, which is not what they bet on
    difficulty.

    Against the pair partner rather than a category baseline, because the
    contrast is between two variants of one change and the baseline's
    feature-dev tasks are a different change; on turns rather than cost,
    because turns is what the runner measures without a price list in it. The
    factors are real bets read off round 1: settings-l3, which had to find the
    rule in the module, took haiku 9 turns against settings-l2's 5 — 1.8x —
    while on sonnet both took 4, which is 1.0 and a miss. 1.2x is well inside
    that spread and can lose on either model.

    Two levels register nothing. A criterion variant has nothing to recover
    and a prose variant is predicted to be cheap and wrong, so neither has an
    honest turns bet to make, and registering one anyway would be
    pre-registering a claim we expect to lose. Absence claims nothing.
    """
    registered = {
        declared(task)["K12"]: task.construction.prediction.effort
        for task in variants(family)
        if task.construction is not None
    }

    assert {
        level: claim for level, claim in registered.items() if claim is not None
    } == family.effort
    assert registered["criterion"] is None
    assert registered["prose"] is None


@pytest.mark.parametrize("family", BY_FAMILY)
def test_no_effort_claim_runs_against_the_reading_burden_order(
    family: Family,
) -> None:
    """The direction guard on the effort half, and the place the two orders
    K12 registers are kept apart.

    An effort claim says its own task costs at least a multiple of its
    partner's, so it may only be held by the member of a pair with more of the
    repository to read — which is `READING`, not the ladder. Prose is third of
    four there and last on the ladder, and that inversion is the finding: the
    guard would fail if a later editor 'fixed' the claims into running
    monotonically along the ladder instead.
    """
    for level, claim in family.effort.items():
        [partner] = [
            other
            for other, pair in family.pairs.items()
            if pair == family.pairs[level] and other != level
        ]
        assert READING.index(level) > READING.index(partner), (
            f"{level} claims {claim.at_least_factor}x its partner {partner}'s "
            "turns while reading less of the repository than it does"
        )
        assert claim.comparator == "pair"
        assert claim.metric == "turns"


@pytest.mark.parametrize("family", BY_FAMILY)
def test_every_prediction_says_why(family: Family) -> None:
    """A rationale is what a missed prediction teaches, and for K12 what it
    has to teach is how the crux reached the solver in that variant — stated,
    pointed at, left in the module, or described."""
    for task in variants(family):
        assert task.construction is not None
        assert len(task.construction.prediction.rationale.split()) >= 15
