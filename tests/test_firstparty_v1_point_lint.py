"""The lint over an `investigation` task: what a points key has to be, and the
two-sided existence proof that its planted points are coverable and its key
discriminates (design note §76.10).

`test_firstparty_v1_point_gate.py` owns the verdict — what the prose an agent
came back with is worth. This suite owns everything that happens *before* an
agent ever sees the task: the authoring invariants `lint_task_set` holds a
point-keyed task to, so that a task nobody could resolve, or one whose key
cannot tell a right answer from a fluent wrong one, is refused at the lint
rather than discovered by a paid sweep.

The read rules are `_points_key_problems` — at least three planted points, an
id and a question in each, no id used twice, a prompt that names the answer
path, and neither the key nor either proof answer shipped inside `repo/` — and
they gate the expensive half exactly as the mutant-set rules gate theirs.

The expensive half is not expensive here, and that is the point of it. This
action's registered **existence proof** runs in both directions and is
**archived**: the author's reference answer must resolve under the point gate
per planted point, their foil answer must fail it, and the lint reads the
rulings `ai-bench prove-points-v1` took at authoring time rather than asking
the grader anything. So `ai-bench lint-v1` stays offline, deterministic and
keyless — a property of the whole command, flags included, which is why the one
affordance that can reach the network is a subcommand beside it.

Nothing here reaches a live grader either. The instrument is
`test_firstparty_v1_point_gate.FakeGrader`, imported rather than copied for the
reason the mutation lint imports its module under test: the two suites are two
questions about one action, and a second fake would drift. What it is given
here that the gate suite does not give it is the *pinned* grader version — an
archive is stamped with the identity of the instrument that took it, and a
proof archive claiming any other version is one of the negatives below.
"""

import hashlib
import json
import re
import textwrap
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from test_firstparty_v1_point_gate import (
    ANSWER_PATH,
    LEDGER,
    WEIGHTS,
    FakeGrader,
    answer,
)

from ai_benchmark import cli, firstparty_v1, point_grader
from ai_benchmark.cli import main
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    EXISTENCE_PROOFS,
    FOIL_ANSWER_FILE,
    REFERENCE_ANSWER_FILE,
    TERRAIN_EXEMPT_ACTIONS,
    ProofSide,
    Task,
    _MINIMUM_POINTS,
    _terrain_problems,
    lint_task_set,
    load_task_set,
    points_key,
    points_key_sha256,
    proof_rulings_file,
    prove_points,
)

TASK_ID = "coalyard-where-the-weight-goes-missing"

PROMPT = f"""\
A day's total is lighter than the loads that made it. Work out why, and write
what you found to {ANSWER_PATH}: what the day loses, where it is lost, and what
you would do about it.
"""

# Three planted points, which is the lint's floor, plus the one disqualifier —
# the plausible wrong answer that sinks a deliverable however much else it
# covered. The ids are what the fake instrument rules on and what the archive
# is keyed by.
POINTS = [
    {
        "id": "the-rounding-site",
        "text": "The answer says weights.net() rounds each load before it is summed.",
    },
    {
        "id": "the-accumulated-error",
        "text": "The answer says the per-load rounding is what the day's total loses.",
    },
    {
        "id": "the-cheapest-repair",
        "text": "The answer argues for rounding the day's total instead of each load.",
    },
]
MORE_POINTS = [
    {
        "id": "the-audit-trail",
        "text": "The answer weighs what the change costs the stored per-load figures.",
    },
    {
        "id": "the-tare-question",
        "text": "The answer considers whether the tare is itself already rounded.",
    },
    {
        "id": "the-scale-resolution",
        "text": "The answer names the weighbridge's own resolution as the floor.",
    },
]
DISQUALIFIERS = [
    {
        "id": "blames-the-scale",
        "text": "The answer claims the weighbridge hardware is miscalibrated.",
    },
]

REFERENCE, FOIL = firstparty_v1.PROOF_SIDES


# --- building a task, its two proof answers, and the archive -------------------


def points_key_json(
    points: list[dict[str, str]],
    disqualifiers: list[dict[str, str]],
    answer_path: str,
) -> str:
    return json.dumps(
        {
            "answer_path": answer_path,
            "points": points,
            "disqualifiers": disqualifiers,
        },
        indent=2,
    )


def write_task(
    root: Path,
    *,
    prompt: str = PROMPT,
    answer_path: str = ANSWER_PATH,
    points: list[dict[str, str]] | None = None,
    disqualifiers: list[dict[str, str]] | None = None,
    reference: str | None = None,
    foil: str | None = None,
    repo: Mapping[str, str] | None = None,
) -> Path:
    """A synthetic `investigation` task, well-formed unless an argument breaks
    it in exactly one way.

    The two proof answers are derived from the planted points rather than
    written out: the reference covers every one of them, and the foil covers
    every one but the last — a plausible answer that misses the load-bearing
    consideration, which is one of the two shapes §76.10 names.
    """
    points = POINTS if points is None else points
    ids = [planted["id"] for planted in points]
    task_dir = root / TASK_ID
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "repo" / "weights.py").write_text(WEIGHTS)
    (task_dir / "repo" / "ledger.py").write_text(LEDGER)
    for name, source in (repo or {}).items():
        path = task_dir / "repo" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    (task_dir / "task.yaml").write_text(
        textwrap.dedent(f"""\
            id: {TASK_ID}
            category: investigation
            scale: cross-file
            surface: application
            language: python
            control: true
            prompt: |
            """)
        + textwrap.indent(prompt, "  ")
    )
    (task_dir / "grading").mkdir()
    (task_dir / "grading" / "points-key.json").write_text(
        points_key_json(
            points, DISQUALIFIERS if disqualifiers is None else disqualifiers, answer_path
        )
    )
    (task_dir / "proofs").mkdir()
    (task_dir / "proofs" / REFERENCE_ANSWER_FILE).write_text(
        answer(*ids) if reference is None else reference
    )
    (task_dir / "proofs" / FOIL_ANSWER_FILE).write_text(
        answer(*ids[:-1]) if foil is None else foil
    )
    return task_dir


def pinned_grader() -> FakeGrader:
    """The fake instrument, stamping the version the lint holds an archive to.

    The version is the instrument's identity — model id plus prompt hash — and
    an archive records which instrument spoke. A fake that stamped its own name
    would be a stale archive, which is a negative below rather than the
    baseline every other test starts from.
    """
    return FakeGrader(version=point_grader.GRADER_VERSION)


def prove(root: Path, grader: FakeGrader | None = None) -> FakeGrader:
    """Take the task's two-sided proof against the fake instrument, through the
    very writer `prove-points-v1` calls — so the baseline the negatives are one
    edit away from is an archive the real writer produced."""
    grader = grader or pinned_grader()
    prove_points(load_task_set(root), lambda: grader)
    return grader


def proved(root: Path, **written: Any) -> Task:
    """A well-formed task with its proof taken: what every negative edits."""
    write_task(root, **written)
    prove(root)
    return loaded(root)


def loaded(root: Path) -> Task:
    [task] = load_task_set(root)
    return task


def problems(root: Path) -> list[str]:
    """What the real lint says about the one task built under this root."""
    return lint_task_set(load_task_set(root))


def only_problem(root: Path) -> str:
    """The lint's single complaint — asserted as single, because every tree here
    is clean but for the one thing under test, and a second problem would mean
    this test is not measuring what it says."""
    [problem] = problems(root)
    return problem


def archive(task: Task, side: ProofSide) -> dict[str, Any]:
    """One side's archived rulings, as JSON."""
    data = json.loads(proof_rulings_file(task, side).read_text())
    assert isinstance(data, dict)
    return data


def rewrite_archive(task: Task, side: ProofSide, **changes: Any) -> None:
    """Edit one side's archive in place — how a proof is made stale in exactly
    one way, without touching the answer or the key it records."""
    proof_rulings_file(task, side).write_text(
        json.dumps(archive(task, side) | changes, indent=2)
    )


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def explode() -> point_grader.PointGrader:
    """A grader factory nothing in the lint may reach."""
    raise AssertionError("the lint constructed a grader")


# --- the well-formed task ------------------------------------------------------


def test_a_well_formed_point_task_lints_clean(tmp_path: Path) -> None:
    """The baseline every negative below is one edit away from: three planted
    points and a disqualifier, a prompt naming the answer path, and an archive
    saying the author's own answer resolves and their foil does not."""
    proved(tmp_path)

    assert problems(tmp_path) == []


def test_the_lint_makes_no_grader_call_on_a_point_keyed_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The property the whole verdict shape's linting rests on. The proof is
    read from the archive, and the pristine grade every task gets collects an
    empty answer file and returns unresolved without asking anything — so a
    corpus holding this task lints with no key exported and no call made."""
    write_task(tmp_path)
    grader = prove(tmp_path)
    taken = len(grader.calls)
    monkeypatch.setattr(point_grader, "deepseek_point_grader", explode)

    assert problems(tmp_path) == []
    assert len(grader.calls) == taken


def test_lint_v1_has_no_flag_that_reaches_the_grader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """"`lint-v1` never calls the LLM" is a claim about the command, not about
    its defaults: a flag that reached the grader would make the glossary's
    sentence true only of an invocation nobody promised to make. So the command
    is run with every flag it has, against a poisoned factory, and its flags are
    then read off its own help — the writer is a subcommand, and not among
    them."""
    proved(tmp_path)
    monkeypatch.setattr(point_grader, "deepseek_point_grader", explode)
    monkeypatch.setenv("COLUMNS", "200")

    main(["lint-v1", "--tasks", str(tmp_path), "--write-hash-gates"])

    assert "lint clean" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["lint-v1", "--help"])
    flags = set(re.findall(r"--[a-z0-9-]+", capsys.readouterr().out))
    assert flags == {"--help", "--tasks", "--write-hash-gates"}


def test_investigation_is_terrain_exempt_at_the_action_level(tmp_path: Path) -> None:
    """An entry with a reason, never a silent non-firing: the rules stop a key
    being grepped out of the workdir, and a planted point is never in the
    workdir. Asserted through `_terrain_problems` as well as through the
    registry, because what the entry buys is the rules not firing."""
    task = proved(tmp_path)

    assert _terrain_problems(task) == []
    assert "never in the workdir" in TERRAIN_EXEMPT_ACTIONS["investigation"]


def test_a_well_formed_point_task_declares_no_terrain_waiver(tmp_path: Path) -> None:
    """The exemption is the action's, so no task of it carries an apology of its
    own — three identical action-shaped reasons in three `task.yaml` files would
    counterfeit a mechanism built to be per task and reason-per-task."""
    assert proved(tmp_path).terrain_waiver == ()


def test_the_actions_proof_form_is_registered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A key with no registered proof form is refused rather than exempt.
    Asserted through the lint's own output rather than by reading the registry:
    what the registry buys is a refusal, and a test that read the dict would
    pass however unwired that dict was."""
    proved(tmp_path)
    monkeypatch.delitem(EXISTENCE_PROOFS, "investigation")

    assert "registers no existence proof" in " ".join(problems(tmp_path))


# --- the read rules: how many points -------------------------------------------


def test_a_key_with_two_points_is_refused(tmp_path: Path) -> None:
    """Below three the universal quantifier barely binds and an answer that
    named one consideration in passing would clear it (§76.10)."""
    proved(tmp_path, points=POINTS[:2])

    problem = only_problem(tmp_path)

    assert "plants 2 point(s)" in problem
    assert f"minimum is {_MINIMUM_POINTS}" in problem


def test_three_points_lint_clean(tmp_path: Path) -> None:
    """The floor binds exactly at three, and the well-formed task is three."""
    assert len(POINTS) == _MINIMUM_POINTS
    proved(tmp_path)

    assert problems(tmp_path) == []


def test_six_points_lint_clean(tmp_path: Path) -> None:
    """There is no maximum. Four to six is §76.10's authoring guidance and
    deliberately not a lint rule, exactly as it is not one for mutants."""
    proved(tmp_path, points=POINTS + MORE_POINTS)

    assert problems(tmp_path) == []


# --- the read rules: the questions and the path --------------------------------


def test_a_point_with_a_blank_question_is_refused(tmp_path: Path) -> None:
    """The model refuses the empty string; a question of spaces gets past
    `min_length=1` and is a question about nothing that every answer covers or
    none does, depending on the mood of the instrument."""
    proved(
        tmp_path,
        points=POINTS[:2] + [{"id": "the-cheapest-repair", "text": "   "}],
    )

    problem = only_problem(tmp_path)

    assert "'the-cheapest-repair' has no text" in problem


def test_a_point_with_a_blank_id_is_refused(tmp_path: Path) -> None:
    """The archive is keyed by id, so a ruling filed under one nobody can name
    is a ruling no later reading of this verdict could match to a question."""
    proved(
        tmp_path,
        points=POINTS[:2] + [{"id": " ", "text": "The answer argues for one repair."}],
    )

    problem = only_problem(tmp_path)

    assert "has a blank id" in problem


def test_an_id_used_twice_is_refused_at_load(tmp_path: Path) -> None:
    """The lint states this rule too, but the loader gets there first and so no
    loaded task ever reaches it: `ai-bench run-live` loads a task set and never
    lints it, so a key whose two questions archive as one ruling has to be
    refused before a paid run, not after."""
    write_task(
        tmp_path,
        points=POINTS[:2] + [dict(POINTS[0])],
        reference=answer(*[planted["id"] for planted in POINTS]),
    )

    with pytest.raises(IngestError, match="id of two of this key"):
        load_task_set(tmp_path)


def test_a_prompt_that_does_not_name_the_answer_path_is_refused(
    tmp_path: Path,
) -> None:
    """An investigation's whole deliverable is the prose at that path, so a task
    whose agent cannot locate it grades every run unresolved for a reason no
    verdict would ever explain."""
    proved(tmp_path, prompt="A day's total is lighter than the loads. Why?\n")

    problem = only_problem(tmp_path)

    assert "the prompt never names the answer file" in problem
    assert "however well it investigated the question" in problem


def test_the_points_key_shipped_in_the_repository_is_refused(tmp_path: Path) -> None:
    """The loader refuses a proofs subtree kept inside `grading/`; this is the
    other direction, and the one that matters to an agent — the required
    elements of the answer handed over with the question."""
    proved(tmp_path, repo={"docs/points-key.json": "{}\n"})

    problem = only_problem(tmp_path)

    assert "docs/points-key.json" in problem
    assert "handed over with the question" in problem


def test_the_reference_answer_shipped_in_the_repository_is_refused(
    tmp_path: Path,
) -> None:
    """The same rule over the other two held-out files: a copy of the author's
    own answer in the starting repository is the whole deliverable."""
    proved(tmp_path, repo={REFERENCE_ANSWER_FILE: "The rounding is per load.\n"})

    assert REFERENCE_ANSWER_FILE in only_problem(tmp_path)


# --- the existence proof: both directions --------------------------------------


def test_a_point_the_reference_answer_does_not_cover_is_refused(
    tmp_path: Path,
) -> None:
    """The unmeetable point, the equivalent mutant's analog: a point the
    author's own answer cannot cover makes the task unresolvable for every agent
    while reading as merely a hard one. The message names the point, because "a
    proof failed" leaves the author to work out which."""
    proved(tmp_path, reference=answer("the-rounding-site", "the-accumulated-error"))

    problem = only_problem(tmp_path)

    assert "reference answer does not resolve" in problem
    assert "'the-cheapest-repair'" in problem


def test_a_reference_answer_making_a_disqualifying_claim_is_refused(
    tmp_path: Path,
) -> None:
    """The other half of the same verdict, and the same failure: an author whose
    own answer is disqualified has planted a disqualifier no answer of theirs
    can avoid."""
    proved(
        tmp_path,
        reference=answer(
            *[planted["id"] for planted in POINTS], "blames-the-scale"
        ),
    )

    problem = only_problem(tmp_path)

    assert "reference answer does not resolve" in problem
    assert "'blames-the-scale'" in problem


def test_a_foil_whose_rulings_resolve_is_refused(tmp_path: Path) -> None:
    """Without this half an always-covered grader passes every positive proof.
    Calibration proves the instrument discriminates in general; the foil proves
    *this key* does."""
    proved(tmp_path, foil=answer(*[planted["id"] for planted in POINTS]))

    problem = only_problem(tmp_path)

    assert "foil answer resolves under the point gate" in problem
    assert "does not discriminate" in problem


def test_a_reference_ruling_quoting_an_absent_span_does_not_count(
    tmp_path: Path,
) -> None:
    """Coverage is not the instrument's word alone, in the proof as in the
    verdict: a covered ruling whose span the answer does not contain is demoted
    by the same `_point_verdict` a run is graded by, so a proof taken over a
    grader that quoted something the author never wrote is not a proof."""
    task = proved(tmp_path)
    rulings = archive(task, REFERENCE)["rulings"]
    rewrite_archive(
        task,
        REFERENCE,
        rulings=[
            entry | {"span": "a sentence the reference answer never contains"}
            if entry["point_id"] == "the-cheapest-repair"
            else entry
            for entry in rulings
        ],
    )

    problem = only_problem(tmp_path)

    assert "reference answer does not resolve" in problem
    assert "'the-cheapest-repair'" in problem


# --- the existence proof: what the archive has to be ---------------------------


def test_an_archive_missing_a_point_the_key_names_is_refused(tmp_path: Path) -> None:
    """The proof is read per planted point and never over the set, for the
    reason the mutation proof is: a set-level reading is exactly where the point
    no answer could cover hides behind its coverable neighbours."""
    task = proved(tmp_path)
    rewrite_archive(
        task,
        REFERENCE,
        rulings=[
            entry
            for entry in archive(task, REFERENCE)["rulings"]
            if entry["point_id"] != "the-accumulated-error"
        ],
    )

    problem = only_problem(tmp_path)

    assert "does not rule on [\"point 'the-accumulated-error'\"]" in problem


def test_an_archive_ruling_on_a_question_the_key_does_not_name_is_refused(
    tmp_path: Path,
) -> None:
    """A ruling about a retired or renamed question is a ruling about a task
    that no longer exists — and an archive holding one was taken before an edit
    nothing else here would catch."""
    task = proved(tmp_path)
    rewrite_archive(
        task,
        FOIL,
        rulings=archive(task, FOIL)["rulings"]
        + [
            {
                "point_id": "a-point-nobody-planted",
                "kind": "point",
                "covered": False,
                "span": None,
                "verified": False,
            }
        ],
    )

    problem = only_problem(tmp_path)

    assert "'a-point-nobody-planted'" in problem
    assert "this key does not name" in problem


def test_a_missing_rulings_archive_is_refused(tmp_path: Path) -> None:
    """An unproved task is one the lint cannot pass, rather than one it would
    prove for you: the lint reads archived rulings and never asks the grader."""
    task = proved(tmp_path)
    proof_rulings_file(task, FOIL).unlink()

    problem = only_problem(tmp_path)

    assert "foil answer has no archived rulings" in problem
    assert "prove-points-v1" in problem


def test_a_missing_foil_answer_is_refused(tmp_path: Path) -> None:
    """The negative half is not optional. A task shipping only a reference
    answer has proved its points coverable and nothing about whether its key
    tells a fluent wrong answer from a right one."""
    task = proved(tmp_path)
    (task.proofs_dir / FOIL_ANSWER_FILE).unlink()

    problem = only_problem(tmp_path)

    assert "foil answer is missing or unreadable" in problem


# --- re-proof triggers on edit -------------------------------------------------


def test_a_stale_grader_version_in_the_archive_is_refused(tmp_path: Path) -> None:
    """The grader is a versioned instrument, and a version change is an edit
    like any other: what the retired instrument said about this answer is not
    what the pinned one would say."""
    write_task(tmp_path)
    prove(tmp_path, FakeGrader(version="deepseek-v4-pro:DeepSeek-V4-Pro-0801:0000deadbeef"))

    reported = problems(tmp_path)

    assert len(reported) == len(firstparty_v1.PROOF_SIDES)
    assert "deepseek-v4-pro:DeepSeek-V4-Pro-0801:0000deadbeef" in reported[0]
    assert point_grader.GRADER_VERSION in reported[0]


def test_an_edited_reference_answer_is_refused_until_it_is_re_proved(
    tmp_path: Path,
) -> None:
    """The mechanism behind "re-proof triggers on edit, not on every lint run":
    the archive records the bytes it was taken against, so an answer edited
    since is one the archived rulings are not about — even, as here, when the
    edit leaves every planted point covered."""
    task = proved(tmp_path)
    edited = task.proofs_dir / REFERENCE_ANSWER_FILE
    edited.write_text(edited.read_text() + "\nOne more paragraph, added later.\n")

    problem = only_problem(tmp_path)

    assert "taken against a different reference answer" in problem
    assert "prove-points-v1" in problem

    prove(tmp_path)
    assert problems(tmp_path) == []


def test_an_edited_points_key_is_refused_until_it_is_re_proved(
    tmp_path: Path,
) -> None:
    """The third hash, and the one an author is likeliest to move: a proof of
    the questions a key used to ask says nothing about the ones it asks now.
    Re-wording a point leaves the ids alone, so nothing but the hash catches
    it."""
    task = proved(tmp_path)
    reworded = [POINTS[0], POINTS[1], POINTS[2] | {"text": "Something else again."}]
    (task.grading_dir / "points-key.json").write_text(
        points_key_json(reworded, DISQUALIFIERS, ANSWER_PATH)
    )

    reported = problems(tmp_path)

    assert len(reported) == len(firstparty_v1.PROOF_SIDES)
    assert all("taken against a different grading/points-key.json" in p for p in reported)


def test_re_indenting_the_points_key_costs_no_re_proof(tmp_path: Path) -> None:
    """The key is hashed over its canonical JSON and not over its file bytes, so
    what triggers a paid re-proof is a change to what the key asks and never a
    change to how it is laid out."""
    task = proved(tmp_path)
    key_file = task.grading_dir / "points-key.json"
    key_file.write_text(json.dumps(json.loads(key_file.read_text())))

    assert problems(tmp_path) == []


# --- the proof writer, as its own subcommand -----------------------------------


def test_prove_points_v1_writes_both_sides_with_the_version_and_the_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The writer, through the subcommand a proof run actually invokes: one call
    per planted point and per disqualifier against each answer, and an archive
    stamped with everything the lint will hold it to."""
    write_task(tmp_path)
    grader = pinned_grader()
    monkeypatch.setattr(point_grader, "deepseek_point_grader", lambda: grader)

    main(["prove-points-v1", "--tasks", str(tmp_path)])

    assert "proved 1 point-keyed task(s)" in capsys.readouterr().out
    task = loaded(tmp_path)
    asked = [planted["id"] for planted in POINTS + DISQUALIFIERS]
    assert grader.calls == asked * 2
    for side in firstparty_v1.PROOF_SIDES:
        written = archive(task, side)
        assert written["grader_version"] == point_grader.GRADER_VERSION
        assert written["points_key_sha256"] == points_key_sha256(points_key(task))
        assert written["answer_sha256"] == sha256(
            (task.proofs_dir / side.answer_file).read_text()
        )
        assert [entry["point_id"] for entry in written["rulings"]] == asked


def test_prove_points_v1_needs_an_exported_api_key(tmp_path: Path) -> None:
    """The one runbook line this command carries, stated where an operator
    reads it: the grader is a live client, so a proof run without the key fails
    at auth resolution rather than at the bar."""
    del tmp_path

    assert "DEEPSEEK_API_KEY" in (cli._prove_points_v1_command.__doc__ or "")


def test_prove_points_v1_archives_what_the_instrument_said_and_judges_nothing(
    tmp_path: Path,
) -> None:
    """The writer records; the lint decides. A foil that resolves is archived
    exactly as one that does not, so that there is one reader of a verdict
    rather than two — and the refusal comes from the lint, offline, where every
    other authoring refusal comes from."""
    proved(tmp_path, foil=answer(*[planted["id"] for planted in POINTS]))

    task = loaded(tmp_path)
    covered = [entry["covered"] for entry in archive(task, FOIL)["rulings"]]

    assert covered == [True, True, True, False]
    assert "foil answer resolves" in only_problem(tmp_path)


def test_prove_points_v1_refuses_an_empty_answer_before_it_calls_anything(
    tmp_path: Path,
) -> None:
    """Loudly, and before any call goes out: grading an answer that is not there
    would archive a proof of nothing and charge for it."""
    write_task(tmp_path, foil="   \n")
    grader = pinned_grader()

    with pytest.raises(IngestError, match="foil answer.*is empty"):
        prove_points(load_task_set(tmp_path), lambda: grader)

    assert grader.calls == [planted["id"] for planted in POINTS + DISQUALIFIERS]


def test_a_corpus_with_no_point_keyed_task_builds_no_grader(tmp_path: Path) -> None:
    """The factory is called on the first answer to grade and never otherwise,
    so a corpus holding no investigation task needs no key — the property
    `eval-v1` already has for a sweep with no point-keyed row."""
    assert prove_points([], explode) == []
