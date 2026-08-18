"""The existence proof of the planted finding ('labels.py', 'matching').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a label names the whole of what is on a handle and
never a part of it. The change asks whether the label wanted is *in* the one
on the tool, which is a substring and not a label, so the shed answers a
request for the saw with the jigsaw as well.
"""

from labels import matching
from shed import Tool


def test_a_label_names_the_whole_of_a_handle_and_never_a_part_of_it():
    tools = [Tool("saw", "wall"), Tool("jigsaw", "bench")]

    assert [tool.label for tool in matching(tools, "saw")] == ["saw"]
