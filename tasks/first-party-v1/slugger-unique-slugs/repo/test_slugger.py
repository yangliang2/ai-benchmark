from slugger import slugify


def test_lowercases_and_hyphenates():
    assert slugify("Hello, World!") == "hello-world"


def test_squeezes_runs_and_trims_edges():
    assert slugify("  --Weekly  Report--  ") == "weekly-report"


def test_a_title_without_alphanumerics_becomes_empty():
    assert slugify("???") == ""
