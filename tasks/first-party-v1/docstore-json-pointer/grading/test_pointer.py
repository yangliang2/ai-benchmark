import pytest
from docstore import DocStore, resolve

DOC = {
    "title": "specs",
    "authors": [{"name": "Ada"}, {"name": "Grace"}],
    "a/b": 1,
    "m~n": 2,
    "~1": "tilde-one",
}


def test_the_empty_pointer_is_the_whole_document():
    assert resolve(DOC, "") is DOC


def test_stepping_into_dicts_by_key():
    assert resolve(DOC, "/title") == "specs"


def test_list_indices_are_zero_based():
    assert resolve(DOC, "/authors/1/name") == "Grace"


def test_tilde_one_escapes_a_slash():
    assert resolve(DOC, "/a~1b") == 1


def test_tilde_zero_escapes_a_tilde():
    assert resolve(DOC, "/m~0n") == 2


def test_escape_decoding_order_keeps_tilde_one_intact():
    assert resolve(DOC, "/~01") == "tilde-one"


def test_a_missing_key_raises_key_error():
    with pytest.raises(KeyError):
        resolve(DOC, "/missing")


def test_an_index_beyond_the_list_raises_key_error():
    with pytest.raises(KeyError):
        resolve(DOC, "/authors/2")


def test_a_pointer_without_a_leading_slash_is_malformed():
    with pytest.raises(ValueError):
        resolve(DOC, "title")


@pytest.mark.parametrize("step", ["01", "-1", "x"])
def test_a_non_integer_list_step_is_malformed(step):
    with pytest.raises(ValueError):
        resolve(DOC, f"/authors/{step}")


def test_fetch_resolves_inside_a_stored_document():
    store = DocStore()
    store.put("paper", DOC)
    assert store.fetch("paper", "/authors/0/name") == "Ada"


def test_existing_get_is_unchanged():
    store = DocStore()
    store.put("paper", DOC)
    assert store.get("paper") is DOC
