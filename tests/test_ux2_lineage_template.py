from pathlib import Path


LINEAGE_TEMPLATE = Path("templates/_ux_completion_panel.html")


def test_lineage_is_collapsed_in_accessible_native_disclosure():
    text = LINEAGE_TEMPLATE.read_text(encoding="utf-8")
    assert "<details>" in text
    assert "<summary>Data Quality &amp; Lineage</summary>" in text
    assert "<details open" not in text
    assert "<table>" in text
    assert "ux_lineage" in text