"""Structural half of the grading suite: asserts the shared bookkeeping was
genuinely pulled up. Fails on the pristine repo, where Exporter is missing."""

from exporters import DelimitedExporter, Exporter, TableExporter


def test_both_exporters_share_one_base():
    assert issubclass(TableExporter, Exporter)
    assert issubclass(DelimitedExporter, Exporter)


def test_the_shared_bookkeeping_lives_on_the_base_alone():
    # Copies left behind in a subclass would shadow the base's methods, so
    # "defined exactly once" means: on Exporter, and on neither subclass.
    for name in ("add", "count"):
        assert name in Exporter.__dict__
        assert name not in TableExporter.__dict__
        assert name not in DelimitedExporter.__dict__


def test_the_shared_constructor_lives_on_the_base():
    assert "__init__" in Exporter.__dict__
    assert "__init__" not in TableExporter.__dict__


def test_each_subclass_keeps_its_own_rendering():
    assert "export" in TableExporter.__dict__
    assert "export" in DelimitedExporter.__dict__
