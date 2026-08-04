import pytest

from docstore import DocStore


def test_put_then_get_returns_the_same_document():
    store = DocStore()
    document = {"title": "specs"}
    store.put("paper", document)
    assert store.get("paper") is document


def test_put_replaces_a_previous_document():
    store = DocStore()
    store.put("paper", {"v": 1})
    store.put("paper", {"v": 2})
    assert store.get("paper") == {"v": 2}


def test_get_of_an_unknown_name_raises():
    with pytest.raises(KeyError):
        DocStore().get("nowhere")


def test_names_are_sorted():
    store = DocStore()
    store.put("b", 1)
    store.put("a", 2)
    assert store.names() == ["a", "b"]
