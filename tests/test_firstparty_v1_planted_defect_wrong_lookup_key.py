"""The sixth planted defect (#56): one wrong key in a lookup, authored as two
tasks that share it.

`postoffice-charge-what-the-scale-said` asks for the fix and
`postoffice-locate-the-wrong-band` asks only for the location, over one
hand-authored starting repository holding one planted defect:
`Window.postage_on` prices a parcel with `to_pay(size_band(...inches))` — the
band the *gauge* put it in — where the card on the wall is priced on the band
the *scale* put it in. Both readings are taken off every parcel, both come back
as a letter A to D, and the card carries a price against all four, so the wrong
key is a key the card holds: nothing raises, nothing is missing, and the money
is read off a neighbouring line of the same card. Same terrain, same defect,
two actions — which is what makes "what does locating cost, as against
fixing?" a reading of the two actions rather than of two repositories.

This suite is #55's, re-aimed at a defect of a different shape. It checks the
same things no other suite can:

- **The two members really do share one repository**, byte for byte. Those
  shared bytes are a checked relation now (design note 45.4): the members are
  deliberately neither a task family nor a pair, so they declare no link, and
  the bytes are how the lint finds the bug-fix partner that is the locate
  member's existence proof. What the lint reads them for is *finding* the
  partner rather than holding the two trees identical, so this is still the
  only thing that says they have not drifted.
- **The defect the fix removes is the defect the key names.** The lint proves
  the answer key discriminates and the reference solution proves the fix
  works, but nothing joins them (36.1). Here the file the fix touches and the
  file every accepted answer names are asserted to be one file.
- **The repository reproduces the symptom nowhere the agent can see it.** On an
  ordinary parcel the two readings agree, every visible fixture that is priced
  is one of those, and the wrong key and the right key name the same line of
  the card. The visible suite exercises the divergence at the level *below* the
  pricing instead — the scale and the gauge put one parcel in different bands,
  and a light awkward parcel is packed into the big sack — so the shape is
  legitimised without the symptom ever being reproduced. Proved here by
  swapping the wrong key for the right one and watching the suite stay green,
  with the vacuous reading refused first by making the lookup raise and
  watching it go red.
- **What the key accepts and refuses on this task's own terrain**: both
  description levels the author wrote down resolve, and every other symbol of
  the defective file does not.
- **The terrain leaves the locating to be done**, the half of it the task-set
  lint cannot see: a band read off a parcel and keyed into something is a shape
  a grep finds in one pass, so the repository does it six times across three
  modules, three on each reading, and five of the six are correct; and the
  contract the defect breaks is written in another file altogether. The
  class-level answer and the prompt's vocabulary are the task-set lint's
  terrain rules now (#65).
- **What no pattern can tell apart**, which is this defect's whole
  discrimination: `Office.sack_for` keys a table off exactly the same
  `size_band(parcel.inches)` and is correct, because the sacks really are
  packed on the gauge. Asserted by running both over one light awkward parcel.
- **This batch's own held-out gate**, carried over from #53: the
  fault-location member hashes the repository it handed over and grades a run
  that edited any of it unresolved, so an agent cannot do the fix work and
  charge it to the locating member. Nothing asserts those digests still
  describe the checked-in tree but this suite.

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, the empty diff grades unresolved — all through the
same execution-verified pipeline real runs go through.
"""

import ast
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    run_for,
    solution_diff,
    solved_tree,
    task_by_id,
    visible_tests_pass,
    workdir_diff,
)

from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    Task,
    _tree_bytes,
    answer_key,
    evaluate,
    is_control,
    lint_task_set,
)

BUG_FIX = "postoffice-charge-what-the-scale-said"
FAULT_LOCATION = "postoffice-locate-the-wrong-band"
MEMBERS = (BUG_FIX, FAULT_LOCATION)

# The file the defect lives in, and the one the fix touches. One name, asserted
# from both sides below.
DEFECTIVE_FILE = "counter.py"
DEFECTIVE_SYMBOL = "Window.postage_on"

ANSWER_PATH = "ANSWER.json"

# The one line the defect is: the price looked up under the band the gauge put
# the parcel in, and the same line with the key the card is actually priced on.
DEFECTIVE_LOOKUP = "        return to_pay(size_band(self.parcel_for(label).inches))\n"
CORRECT_LOOKUP = "        return to_pay(weight_band(self.parcel_for(label).grams))\n"

# Every place in the repository where a band is read off a parcel and keyed
# into something, as (file, symbol, reading) — read and never added to. Named
# here because the terrain claim is that a grep for the shape finds six sites,
# evenly split between the two readings, and has to read all six.
READINGS = {
    ("parcels.py", "to_the_scale", "weight_band"),
    ("parcels.py", "to_the_gauge", "size_band"),
    (DEFECTIVE_FILE, "Window.weighed", "weight_band"),
    (DEFECTIVE_FILE, DEFECTIVE_SYMBOL, "size_band"),
    ("office.py", "Office.sack_for", "size_band"),
    ("office.py", "Office.two_to_carry", "weight_band"),
}

# The contract the defect breaks, in the repository's own words and in another
# file altogether — deliberately not the prompt's, so that reading the prompt
# is not one grep away from the defective file, which the task-set lint's
# terrain rules now check for (#65).
CONTRACT = (
    "Which line of it a parcel is charged at is settled by what the parcel "
    "weighed: the office has priced by the scale since the day it opened, and "
    "what the gauge makes of a parcel has never had anything to do with the "
    "money."
)
CONTRACT_FILE = "card.py"

# The parcel the prompt reports: next to no weight in it, and a great awkward
# thing round the middle. Band B on the scale and band C on the gauge.
AWKWARD = ("a lampshade", 300, 40)


def repo_source(file: str) -> str:
    return (task_by_id(FAULT_LOCATION).repo_dir / file).read_text(encoding="utf-8")


def function(source: str, symbol: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """The `def` a bare name or a `Class.method` spelling names."""
    enclosing, _, name = symbol.rpartition(".")
    body = ast.parse(source).body
    if enclosing:
        [holder] = [
            node
            for node in body
            if isinstance(node, ast.ClassDef) and node.name == enclosing
        ]
        body = holder.body
    [found] = [
        node
        for node in body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name == name
    ]
    return found


def functions(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function a module defines, methods spelled `Class.method`."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                    found[f"{node.name}.{member.name}"] = member
    return found


def code_files() -> list[Path]:
    """The repository's modules, its own test suite left out."""
    return [
        path
        for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("*.py"))
        if not path.name.startswith("test_")
    ]


def answers(payload: str, *, at: str = ANSWER_PATH) -> Callable[[Path], None]:
    """The edit a run that wrote this answer file would log."""

    def write(workdir: Path) -> None:
        target = workdir / at
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload)

    return write


def naming(file: str, symbol: str) -> str:
    return json.dumps({"file": file, "symbol": symbol}, indent=2) + "\n"


def verdict(task: Task, edit: Callable[[Path], None]) -> float:
    """What the pipeline a real run replays through makes of this run."""
    return evaluate(
        [task], [run_for(task, workdir_diff(task, edit))], source="run-log"
    )[0].quality_value


# --- one repository, one defect, two actions -----------------------------------


def test_the_two_members_share_one_starting_repository() -> None:
    """Byte for byte, and checked here because nothing else checks it: the two
    are deliberately neither a task family nor a pair — those constructs
    require one varied knob and an agreed category, and these vary no knob and
    differ in category — so the family lint's peer-to-peer tree comparison
    never runs over them."""
    fix, locate = task_by_id(BUG_FIX), task_by_id(FAULT_LOCATION)

    assert _tree_bytes(fix.repo_dir) == _tree_bytes(locate.repo_dir)


def test_the_defect_the_fix_removes_is_the_defect_the_key_names() -> None:
    """The join the corpus cannot make on its own.

    A fault-location task's grading proves only that its grading test tells an
    accepted answer from a wrong one; what proves there is a defect to find at
    all is the paired bug-fix member's held-out tests failing on the shared
    pristine repository — its registered existence proof (45.4). What that proof
    does not reach is whether the two are about the *same* defect, so the two
    halves are tied together here: every file the accepted answers name is the
    one file the reference fix touches.
    """
    fix = task_by_id(BUG_FIX)
    key = answer_key(task_by_id(FAULT_LOCATION))

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(fix).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {DEFECTIVE_FILE}
    assert {answer.file for answer in key.accepted} == {DEFECTIVE_FILE}


def test_the_fix_is_the_key_swapped_and_nothing_else() -> None:
    """One planted defect and no other seeded fault: the whole of the reference
    solution is the key of one lookup swapped for the reading the card is
    priced on — and the import the wrong key was that module's only user of —
    so the terrain the fault-location member is measured over holds exactly one
    thing to find."""
    changed = [
        line
        for line in solution_diff(task_by_id(BUG_FIX)).splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]

    assert changed == [
        "-from parcels import size_band, weight_band",
        "+from parcels import weight_band",
        f"-{DEFECTIVE_LOOKUP.rstrip()}",
        f"+{CORRECT_LOOKUP.rstrip()}",
    ]


def test_neither_member_claims_anything_about_difficulty() -> None:
    """Both are coverage tasks: authored to fill a category, betting nothing.
    Outside the frozen 22 that has to be said outright, and saying it is also
    what keeps them out of every knob reading — a task declaring no
    construction can join no family, no pair and no effort claim, so neither
    can advance a knob's counter or move a published multiplier."""
    for task_id in MEMBERS:
        task = task_by_id(task_id)

        assert task.control
        assert is_control(task)
        assert task.construction is None


def test_each_member_is_declared_as_designed() -> None:
    fix, locate = task_by_id(BUG_FIX), task_by_id(FAULT_LOCATION)

    assert (fix.category, fix.scale, fix.language) == (
        "bug-fix", "single-file", "python",
    )
    assert (locate.category, locate.scale, locate.language) == (
        "fault-location", "single-file", "python",
    )


# --- the symptom is visible and its cause is not -------------------------------


def test_the_repository_reproduces_the_symptom_in_no_visible_test() -> None:
    """The convention this batch holds to: a failing test in the starting
    repository would point straight at the defect and delete the action both
    members measure. So the repository's own suite is green while the defect
    is in it — the symptom reaches the agent through the prompt alone."""
    for task_id in MEMBERS:
        assert visible_tests_pass(task_by_id(task_id))


def test_the_visible_suite_stays_green_on_the_fix() -> None:
    """The other direction: the fix is a fix and not a rewrite — everything
    the repository already asserted about itself still holds."""
    fix = task_by_id(BUG_FIX)

    assert visible_tests_pass(fix, edit=solved_tree(fix))


def swapping(what: str, into: str, *, inside: str = DEFECTIVE_FILE) -> Callable[
    [Path], None
]:
    """One exact substitution in a module of the starting repository."""

    def edit(workdir: Path) -> None:
        source = workdir / inside
        text = source.read_text(encoding="utf-8")
        changed = text.replace(what, into)
        assert changed != text, f"{what!r} is no longer in {inside}"
        source.write_text(changed, encoding="utf-8")

    return edit


def test_no_visible_test_prices_a_parcel_the_two_readings_disagree_about(
) -> None:
    """*Why* the visible suite is green, asserted rather than hoped for.

    A wrong key is invisible to every test whose fixtures make the wrong key
    and the right key name the same entry, and the repository is written so
    that nothing visible prices a parcel the scale and the gauge put in
    different bands. It exercises such a parcel one level down instead — the
    two band functions disagree about it, `to_the_scale` and `to_the_gauge`
    pick out different parcels of one day, and a light awkward one is packed
    into the big sack — which legitimises the shape in the repository's own
    voice without reproducing the symptom. That is this defect's version of
    #52's "every visible fixture stands at the boundary", and it is a property
    of the fixtures rather than of the code, which would be silently lost the
    first time a visible test priced an awkward parcel.

    Asserted by putting the right key in: if the suite stays green with the
    defect repaired, no visible test could ever have told the two apart.

    The vacuous reading is refused first: with the lookup made to raise, the
    suite has to go red, or nothing visible prices anything at all and the
    green above is about nothing.
    """
    locate = task_by_id(FAULT_LOCATION)

    assert not visible_tests_pass(
        locate,
        edit=swapping(
            DEFECTIVE_LOOKUP,
            '        raise AssertionError("a price was looked up")\n',
        ),
    )
    assert visible_tests_pass(locate, edit=swapping(DEFECTIVE_LOOKUP, CORRECT_LOOKUP))


def test_each_prompt_states_the_symptom_and_not_its_cause() -> None:
    """Both members do the same detective work; only the deliverable differs.
    A prompt naming the defective module or method would make the
    fault-location task a transcription exercise."""
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "post office" in prompt
        for giveaway in (
            DEFECTIVE_FILE, "counter", "Window", "window", "postage", "Charge",
            "band", "lookup", "key", "size_band", "weight_band", "inches",
            "grams", "POSTAGE",
        ):
            assert giveaway not in prompt, f"{task_id} names {giveaway}"


def test_both_prompts_state_the_intended_behaviour() -> None:
    """Parity of information about what correct *is*, not identical text.

    #51 found the fix member told what correct was while the locate member had
    to infer it, which understates the fix side of the very comparison the two
    members exist to produce. Here the symptom paragraph is one text in both
    and the rule is stated in both: what separates them is the deliverable
    paragraph alone. Saying what correct is leaks no location.
    """
    prompts = [task_by_id(task_id).prompt for task_id in MEMBERS]
    symptom = "Something has gone wrong at the post office."

    for prompt in prompts:
        flowed = " ".join(prompt.split())
        assert "read off the card against what the scale made of it" in flowed
        assert "settles which sack it leaves in" in flowed
        assert prompt.startswith(symptom)
    reported = {"\n\n".join(prompt.split("\n\n")[:2]) for prompt in prompts}
    assert len(reported) == 1, "the two members report different symptoms"


# --- the terrain leaves the locating to be done --------------------------------


def readings_taken() -> set[tuple[str, str, str]]:
    """Every (file, symbol, reading) where a band is read off a parcel."""
    found = set()
    for path in code_files():
        for name, node in functions(path.read_text(encoding="utf-8")).items():
            for call in ast.walk(node):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id in {"weight_band", "size_band"}
                ):
                    found.add((path.name, name, call.func.id))
    return found


def test_the_defect_is_not_the_only_reading_keyed_into_something() -> None:
    """A single band read off a parcel makes locating a grep.

    It is a shape a grep finds in one pass, so the repository reads a band off
    a parcel six times, across three modules, and five of them are correct:
    `parcels.to_the_scale` and `parcels.to_the_gauge` pick a day's parcels out
    by either reading, `Window.weighed` is what the scale made of one parcel,
    `Office.sack_for` packs the sacks off the gauge, and `Office.two_to_carry`
    reads the scale into who carries a parcel out to the van.

    The other half of the same claim, and the half that decides this defect:
    three of the six read the scale and three read the gauge, so the shape a
    reader would filter on — a lookup keyed on the gauge — still names three
    sites, and which of them is wrong is settled by what the lookup is *for*
    rather than by the pattern. The defective module holds a correct one of its
    own, so reaching the right file finishes nothing.
    """
    found = readings_taken()

    assert found == READINGS
    assert len({file for file, *_ in found}) == 3
    assert len([reading for *_, reading in found if reading == "size_band"]) == 3
    assert len([reading for *_, reading in found if reading == "weight_band"]) == 3
    assert len([file for file, *_ in found if file == DEFECTIVE_FILE]) == 2


def test_the_repository_declares_the_shape_it_uses_correctly() -> None:
    """Why the five correct ones are not merely five more places to look.

    They are asserted by the repository's own tests, so the shape is
    *legitimised* rather than left ambiguous: an agent reading the visible
    suite is told, in the repository's own voice, that reading a band off a
    parcel and keying it into something is how this office works. And the
    visible suite says outright that the two readings need not agree — the
    scale and the gauge put one parcel in different bands, they pick out
    different parcels of one day, and a light awkward parcel goes in the big
    sack all the same — so the concept is present everywhere except where the
    wrong one of the two is used.
    """
    suite = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("test_*.py"))
    )

    for declared in (
        "def test_a_light_parcel_can_be_an_awkward_one_all_the_same",
        "def test_a_heavy_parcel_can_be_a_neat_one_just_as_easily",
        "def test_the_two_readings_pick_out_different_parcels_of_a_day",
        "def test_what_the_scale_made_of_a_parcel_is_the_band_it_goes_in",
        "def test_the_sack_a_parcel_leaves_in_is_the_one_the_gauge_puts_it_in",
        "def test_a_light_awkward_parcel_still_goes_in_the_sack_it_will_fit_in",
    ):
        assert declared in suite, f"the visible suite no longer says {declared}"


def test_the_nearest_twin_is_the_same_key_used_correctly() -> None:
    """This defect's whole discrimination, run rather than described.

    `Office.sack_for` and `Window.postage_on` key a table off the very same
    `size_band(parcel.inches)`, in the same shape, one line of code each. One
    is correct and one is the defect, and what separates them is only what the
    table is for: the sacks really are packed on the gauge, and the card really
    is priced on the scale. Nothing a grep or a linter sees tells them apart —
    so this is asserted by running both over one light awkward parcel, beside
    what the card says against the band that parcel actually weighed.
    """
    import shutil
    import subprocess
    import sys
    import tempfile

    label, grams, inches = AWKWARD
    with tempfile.TemporaryDirectory(prefix="ai-bench-twin-") as name:
        # A throwaway copy, because importing writes bytecode and the
        # checked-in `repo/` trees of swept tasks are immutable.
        workdir = Path(name)
        shutil.copytree(
            task_by_id(FAULT_LOCATION).repo_dir, workdir, dirs_exist_ok=True
        )
        asked = subprocess.run(
            [
                sys.executable,
                "-c",
                "from card import to_pay\n"
                "from counter import Window\n"
                "from office import Office\n"
                "from parcels import Parcel, weight_band\n"
                f"parcel = Parcel({label!r}, {grams!r}, {inches!r})\n"
                "day = Window([parcel])\n"
                f"print(Office().sack_for(day, {label!r}))\n"
                f"print(day.postage_on({label!r}))\n"
                "print(to_pay(weight_band(parcel.grams)))\n",
            ],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()

    assert asked == ["the", "big", "sack", "340", "235"]


def test_the_contract_is_not_written_on_top_of_the_defect() -> None:
    """Honest, and not in one glance.

    Which of the two readings the card is priced on is the whole of the
    inference, so a docstring saying so three lines above the lookup that gets
    it wrong removes the last step of the work. It is stated once, in the
    module docstring of another file altogether — card.py, which is where the
    prices the prompt quotes come from — and the defective module says only
    that the window prices what was brought in off the card, which is true and
    decides nothing. The defective method's own docstring says what the method
    is for and is silent about which reading it is looked up under.
    """
    card = repo_source(CONTRACT_FILE)
    defective = repo_source(DEFECTIVE_FILE)
    docstring = " ".join((ast.get_docstring(ast.parse(card)) or "").split())

    assert " ".join(CONTRACT.split()) in docstring
    for said in ("priced by the scale", "what the scale made", "to do with the money"):
        assert said not in defective, f"{DEFECTIVE_FILE} states the contract: {said}"
    assert ast.get_docstring(function(defective, DEFECTIVE_SYMBOL)) == (
        "What one parcel comes to, off the card on the wall."
    )


# --- the gates every checked-in task passes ------------------------------------


def test_the_two_members_lint_clean_together() -> None:
    """Linted as the two members they are rather than one at a time: the locate
    member's existence proof is the bug-fix member's failure on the starting
    repository they share (design note 45.4), so a set holding only one of them
    is one in which the locate task has nothing saying there is a defect in it
    to find."""
    assert lint_task_set([task_by_id(member) for member in MEMBERS]) == []


@pytest.mark.parametrize("task_id", MEMBERS)
def test_reference_solution_resolves_and_doing_nothing_does_not(
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


@pytest.mark.parametrize("task_id", MEMBERS)
def test_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    """Single-file both ways, and for different reasons: the fix is one edit to
    one module, and the located fault is one answer file written into the
    workdir."""
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert len(touched) == 1


# --- what each member's grading makes of a near-miss ---------------------------


def test_a_fix_that_moves_the_gauge_instead_of_the_key_is_not_the_fix() -> None:
    """The near-miss this defect invites, graded rather than assumed.

    The symptom is one parcel charged a line too far down the card, so the
    shortest thing that looks like a cure is to move the line the gauge draws
    until that parcel falls the other side of it. The money then comes out
    right for the parcel the prompt reports, and the sacks come out wrong: the
    lampshade is sent off in the small sack it does not fit in. The prompt says
    outright that the sack it went in was the one it belonged in, and the
    held-out tests grade the near-miss unresolved.
    """
    fix = task_by_id(BUG_FIX)
    moved = swapping(
        'BY_THE_GAUGE = ((18, "A"), (30, "B"), (48, "C"), (72, "D"))',
        'BY_THE_GAUGE = ((18, "A"), (48, "B"), (60, "C"), (72, "D"))',
        inside="parcels.py",
    )

    assert verdict(fix, moved) == 0.0


@pytest.mark.parametrize("symbol", ["Window.postage_on", "Window", "postage_on"])
def test_every_description_level_the_author_wrote_down_resolves(
    symbol: str,
) -> None:
    """The defective method and the class enclosing it are both legitimately
    correct descriptions of this defect, so both are in the key — and the bare
    method name, which is how an agent phrases an answer about something
    nested, answers the qualified one it is spelled from."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 1.0


@pytest.mark.parametrize(
    "symbol",
    [
        "Window.weighed", "weighed", "Window.parcel_for", "parcel_for",
        "Window.handed_in", "Window.charge_for", "charge_for", "Charge",
        "Charge.written_up", "written_up", "most_charged", "NOTHING_TAKEN",
    ],
)
def test_every_other_symbol_of_the_defective_file_is_unresolved(
    symbol: str,
) -> None:
    """Every other site in the defective module, each of which an agent has to
    read and rule out: `Window.weighed` is the module's other reading of a band
    off a parcel and is correct, `Window.parcel_for` is what the wrong key's
    lookup reads its parcel from, `Window.handed_in` decides which parcels are
    priced at all, `Window.charge_for` is the caller that carries the wrong
    figure into the book, `Charge` — the second class, the one that makes
    naming `Window` a choice — is one parcel priced up, `Charge.written_up` is
    where the money reaches the book, `most_charged` reads a day whole, and
    `NOTHING_TAKEN` is what the module puts where nothing was taken. All of
    them are correct, so an answer naming one has read the right file and not
    found the defect."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 0.0


def test_the_key_writes_down_the_plausible_wrong_files() -> None:
    """The near-misses no lint can invent, and the judgement 36.3 asks be spent
    on files the accepted set does not name.

    `card.py` is the module the symptom points at first: the two prices the
    prompt quotes are both on that card, and a card with the wrong money on it
    would produce exactly the complaint that was made. `parcels.py` is where a
    reading becomes a band at all, and holds both of the functions the wrong
    key is a choice between. `office.py` is where the takings that came out
    over are added up, and `Office.sack_for` is the correct twin of the
    defective line. Every one of them is run through the real pipeline by the
    lint and required to grade unresolved.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    assert key.rejected
    assert {answer.file for answer in key.rejected} == {
        "card.py", "parcels.py", "office.py",
    }
    named = {(answer.file, answer.symbol) for answer in key.rejected}
    assert ("card.py", "to_pay") in named
    assert ("card.py", "POSTAGE") in named
    assert ("parcels.py", "size_band") in named
    assert ("office.py", "Office.sack_for") in named


def test_the_answer_key_ships_held_out_and_the_repository_carries_no_answer(
) -> None:
    """Held out of the workdir: the key travels with the grading directory the
    overlay copies at grade time, and the pristine repository the agent is
    given carries neither it nor an answer file."""
    locate = task_by_id(FAULT_LOCATION)

    assert (locate.grading_dir / ANSWER_KEY_FILE).is_file()
    assert not (locate.repo_dir / ANSWER_KEY_FILE).exists()
    assert not (locate.repo_dir / ANSWER_PATH).exists()


# --- this batch's own gate: locating is not fixing -----------------------------


def test_a_correct_answer_that_also_repaired_the_code_is_unresolved() -> None:
    """What the second held-out test is for, and what nothing else can show.

    The two members exist to produce one number — what locating costs, as
    against fixing — so a run that does the fix work and then writes a correct
    answer would resolve at fix-member cost with nothing in the log to say it
    happened. The prompt forbids it and this makes the prompt binding: the same
    answer that resolves on its own grades unresolved once the repair rides
    along with it.
    """
    locate = task_by_id(FAULT_LOCATION)
    accepted = naming(DEFECTIVE_FILE, DEFECTIVE_SYMBOL)

    def answered_and_repaired(workdir: Path) -> None:
        answers(accepted)(workdir)
        swapping(DEFECTIVE_LOOKUP, CORRECT_LOOKUP)(workdir)

    assert verdict(locate, answers(accepted)) == 1.0
    assert verdict(locate, answered_and_repaired) == 0.0


def test_reading_the_repository_leaves_it_as_it_was_found() -> None:
    """What the gate does *not* forbid, which is as much of it as what it does:
    a scratch file or a note left behind by an agent that read the code is not
    a repair, and only the files handed over are compared. A gate that failed
    on those would grade an honest run unresolved for having taken notes."""
    locate = task_by_id(FAULT_LOCATION)
    accepted = naming(DEFECTIVE_FILE, DEFECTIVE_SYMBOL)

    def answered_with_notes(workdir: Path) -> None:
        answers(accepted)(workdir)
        (workdir / "notes.md").write_text("the money follows the wrong reading\n")

    assert verdict(locate, answered_with_notes) == 1.0
