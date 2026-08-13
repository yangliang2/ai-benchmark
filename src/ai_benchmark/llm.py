"""The live LLM classifier: Claude Opus 5 with structured output.

Only constructed on cache misses — a warm cache never touches the network.
Server-side refusal fallback is enabled by default per Anthropic guidance.
"""

import json
from typing import get_args

from ai_benchmark.classify import Classifier, Label
from ai_benchmark.instances import InstanceContext
from ai_benchmark.schema import Scale, TaskCategory

# Derived from the schema Literals so the taxonomy has one source of truth.
CATEGORIES: list[TaskCategory] = list(get_args(TaskCategory))
SCALES: list[Scale] = list(get_args(Scale))

LABEL_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "scale": {"type": "string", "enum": SCALES},
        "language": {"type": ["string", "null"]},
    },
    "required": ["category", "scale", "language"],
    "additionalProperties": False,
}

# One gloss per category, keyed by the vocabulary rather than repeating it:
# the listing below is built by walking CATEGORIES, so a category added to the
# schema and left unglossed here fails loudly at import rather than quietly
# going unoffered to the classifier.
GLOSSES: dict[TaskCategory, str] = {
    "bug-fix": "correct existing behaviour that is wrong (SWE-bench-style issue->patch)",
    "feature-dev": "add new user-visible capability",
    "refactor": "behaviour-preserving restructuring",
    "test-authoring": "tests are the primary deliverable",
    "codebase-comprehension": "answer questions about code without changing it",
    "fault-location": "say where a defect lives, without fixing it",
    "code-review": "judge a diff someone else wrote",
    "investigation": "investigate an open question and propose an answer",
    "requirement-decomposition": "break a requirement into workable pieces",
    "performance-optimisation": "make existing behaviour faster or cheaper",
    "unclassified": (
        "use this whenever you cannot determine the category with reasonable "
        "confidence from the information given — never force-fit"
    ),
}

CATEGORY_LISTING = "\n".join(
    f"- {category}: {GLOSSES[category]}" for category in CATEGORIES
)

PROMPT = f"""Classify this software-engineering benchmark instance into the task taxonomy.

Benchmark: {{benchmark}}
Instance id: {{instance_id}}
{{context}}
Categories (pick exactly one — the engineering action the task asks for; where
a task chains several actions, its primary deliverable decides):
{CATEGORY_LISTING}

Also give:
- scale: "single-file" if edits are confined to one file, "cross-file" if they
  span files, "unknown" if you cannot tell
- language: the primary language of the task's repo, lowercase (e.g. "python"),
  or null if unknown
"""

# Enough to convey the ask without blowing up cost on long issue threads.
_PROBLEM_STATEMENT_LIMIT = 4000


def build_prompt(
    benchmark: str, instance_id: str, context: InstanceContext | None
) -> str:
    """Fold whatever instance evidence we have into the prompt (#8)."""
    parts = []
    if context is not None:
        if statement := context["problem_statement"]:
            if len(statement) > _PROBLEM_STATEMENT_LIMIT:
                statement = statement[:_PROBLEM_STATEMENT_LIMIT] + "\n[truncated]"
            parts.append("Problem statement:\n" + statement + "\n")
        if files := context["patch_files"]:
            parts.append(
                "Files changed by the reference solution:\n"
                + "\n".join(f"- {f}" for f in files)
                + "\n"
            )
    return PROMPT.format(
        benchmark=benchmark,
        instance_id=instance_id,
        context="\n" + "\n".join(parts) if parts else "",
    )


def anthropic_classifier() -> Classifier:
    import anthropic

    client = anthropic.Anthropic()

    def classify(
        benchmark: str, instance_id: str, context: InstanceContext | None
    ) -> Label:
        # Thinking is on by default on claude-opus-5 and max_tokens caps
        # thinking + response text together — keep generous headroom.
        response = client.beta.messages.create(
            model="claude-opus-5",
            max_tokens=16000,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": LABEL_SCHEMA},
            },
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
            messages=[
                {
                    "role": "user",
                    "content": build_prompt(benchmark, instance_id, context),
                }
            ],
        )
        if response.stop_reason == "refusal":
            return Label(category="unclassified", scale="unknown", language=None)
        if response.stop_reason == "max_tokens":
            # Truncated JSON must not be parsed into a half-right label (it
            # would be cached); fail loudly instead.
            raise RuntimeError(
                f"classification of {benchmark}/{instance_id} was truncated "
                "(stop_reason=max_tokens); raise max_tokens and re-run"
            )
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        return Label(
            category=data["category"], scale=data["scale"], language=data["language"]
        )

    return classify
