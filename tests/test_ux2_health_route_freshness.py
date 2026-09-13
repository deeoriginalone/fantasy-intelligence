from pathlib import Path


def test_team_route_uses_sleeper_health_source_without_csv_fallback():
    text = Path("owner_operations.py").read_text(encoding="utf-8")
    start = text.index('@bp.route("/team")')
    end = text.index('@bp.route("/lineup")', start)
    segment = text[start:end]
    assert "health_freshness_from_report_date" in segment
    assert "team_health_contract(roster, source=health_source, **health_meta)" in segment
    assert "injury_reports" not in segment


def test_team_route_supports_suffix_tolerant_player_identity_lookup():
    text = Path("owner_operations.py").read_text(encoding="utf-8")
    assert "normalized_name = normalize_player_name(name)" in text
    assert "LIKE %s" in text