"""The live LLM classifier: Claude Opus 5 with structured output.

Only constructed on cache misses — a warm cache never touches the network.
Server-side refusal fallback is enabled by default per Anthropic guidance.
"""

import json

from ai_benchmark.classify import Classifier, Label
from ai_benchmark.schema import Scale, TaskCategory

CATEGORIES: list[TaskCategory] = [
    "bug-fix",
    "feature-dev",
    "refactor",
    "test-authoring",
    "frontend-ui",
    "infra-config",
    "codebase-comprehension",
    "unclassified",
]

SCALES: list[Scale] = ["single-file", "cross-file", "unknown"]

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

PROMPT = """Classify this software-engineering benchmark instance into the task taxonomy.

Benchmark: {benchmark}
Instance id: {instance_id}

Categories (pick exactly one, by the primary deliverable of the task):
- bug-fix: correct existing behaviour that is wrong (SWE-bench-style issue->patch)
- feature-dev: add new user-visible capability
- refactor: behaviour-preserving restructuring
- test-authoring: tests are the primary deliverable
- frontend-ui: visual interface implementation
- infra-config: build, CI/CD, deployment, dependencies, configuration
- codebase-comprehension: answer questions about code without changing it
- unclassified: use this whenever you cannot determine the category with
  reasonable confidence from the information given — never force-fit

Also give:
- scale: "single-file" if edits are confined to one file, "cross-file" if they
  span files, "unknown" if you cannot tell
- language: the primary language of the task's repo, lowercase (e.g. "python"),
  or null if unknown
"""


def anthropic_classifier() -> Classifier:
    import anthropic

    client = anthropic.Anthropic()

    def classify(benchmark: str, instance_id: str) -> Label:
        response = client.beta.messages.create(
            model="claude-opus-5",
            max_tokens=4096,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": LABEL_SCHEMA},
            },
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(benchmark=benchmark, instance_id=instance_id),
                }
            ],
        )
        if response.stop_reason == "refusal":
            return Label(category="unclassified", scale="unknown", language=None)
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        return Label(
            category=data["category"], scale=data["scale"], language=data["language"]
        )

    return classify
