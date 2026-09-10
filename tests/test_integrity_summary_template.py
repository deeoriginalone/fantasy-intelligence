from pathlib import Path


def read(name):
    return Path(name).read_text(encoding="utf-8")


def test_shared_integrity_component_renders_verified_contract_fields():
    text = read("templates/_integrity_summary.html")
    for marker in (
        "recommendation_ready",
        "completeness_score",
        "confidence.score",
        "freshness.score",
        "freshness.domains.items()",
        "unknown_health_players",
        "missing_matchups",
        "integrity.blockers",
    ):
        assert marker in text


def test_lineup_template_includes_shared_integrity_component():
    text = read("templates/lineup.html")
    assert "{% set integrity = lineup_intelligence.integrity %}" in text
    assert "{% include '_integrity_summary.html' %}" in text


def test_gm_template_includes_lineup_integrity_component():
    text = read("templates/gm.html")
    assert "{% set integrity = lineup_intelligence.integrity %}" in text
    assert "Weekly Command Center Integrity" in text
    assert "{% include '_integrity_summary.html' %}" in text


def test_component_does_not_recalculate_integrity_scores():
    text = read("templates/_integrity_summary.html")
    assert "calculate_" not in text
    assert "build_integrity" not in text
