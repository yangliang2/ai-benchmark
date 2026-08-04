import pytest

from template import render


def test_plain_placeholders_still_render():
    assert render("Hello {{ name }}", {"name": "Ada"}) == "Hello Ada"


def test_filters_still_apply():
    assert render("{{ name|upper }}", {"name": "ada"}) == "ADA"


def test_the_title_filter():
    assert render("{{ name|title }}", {"name": "ada LOVELACE"}) == "Ada Lovelace"


def test_the_trim_filter():
    assert render("{{ name|trim }}", {"name": "  ada  "}) == "ada"


def test_a_loop_renders_its_body_once_per_element():
    template = "{% for x in xs %}{{ x }},{% endfor %}"
    assert render(template, {"xs": [1, 2, 3]}) == "1,2,3,"


def test_a_loop_over_an_empty_list_renders_nothing():
    template = "a{% for x in xs %}{{ x }}{% endfor %}b"
    assert render(template, {"xs": []}) == "ab"


def test_loops_nest():
    template = (
        "{% for row in rows %}{% for cell in row %}{{ cell }}{% endfor %};"
        "{% endfor %}"
    )
    assert render(template, {"rows": [["a", "b"], ["c"]]}) == "ab;c;"


def test_the_loop_variable_shadows_and_restores_the_outer_value():
    template = "{% for x in xs %}{{ x }}{% endfor %}{{ x }}"
    assert render(template, {"xs": ["1", "2"], "x": "z"}) == "12z"


def test_filters_work_inside_a_loop_body():
    template = "{% for word in words %}{{ word|upper }} {% endfor %}"
    assert render(template, {"words": ["a", "b"]}) == "A B "


def test_an_unclosed_loop_raises():
    with pytest.raises(ValueError):
        render("{% for x in xs %}oops", {"xs": []})


def test_a_stray_endfor_raises():
    with pytest.raises(ValueError):
        render("a{% endfor %}", {})


def test_a_missing_name_still_raises_key_error():
    with pytest.raises(KeyError):
        render("{{ ghost }}", {})
