from pathlib import Path

def test_team_route_builds_and_supplies_accuracy_contract():
    text=Path("owner_operations.py").read_text(encoding="utf-8")
    start=text.index('@bp.route("/team")'); end=text.index('@bp.route("/lineup")',start); segment=text[start:end]
    for expected in ("build_team_accuracy_contract","team_accuracy=team_accuracy","league_settings=league_settings","team_needs=team_needs","team_health=team_health","build_team_priority_action","team_priority_action=team_priority_action"):
        assert expected in segment


def test_team_route_uses_team_health_freshness_for_player_targeting():
    text = Path("owner_operations.py").read_text(encoding="utf-8")
    start = text.index('@bp.route("/team")')
    end = text.index('@bp.route("/lineup")', start)
    segment = text[start:end]
    assert 'health_freshness = team_health.get("freshness_state")' in segment
    assert 'blocker=(team_health.get("blocker") if team_health.get("state") == "BLOCKED" else None)' in segment


def test_team_route_preserves_missing_weekly_score():
    text=Path("owner_operations.py").read_text(encoding="utf-8")
    start=text.index('@bp.route("/team")')
    end=text.index('@bp.route("/lineup")',start)
    segment=text[start:end]
    assert '"weekly_score": None' in segment
    assert "weekly_starter_score" not in segment

def test_team_route_derives_summary_from_shared_team_needs_result():
    text = Path("owner_operations.py").read_text(encoding="utf-8")
    start = text.index('@bp.route("/team")')
    end = text.index('@bp.route("/lineup")', start)
    segment = text[start:end]

    assert "team_needs = team_needs_contract(roster, league_settings)" in segment
    assert "needs = build_team_needs_summary(team_needs)" in segment
    assert segment.index("team_needs = team_needs_contract") < segment.index(
        "needs = build_team_needs_summary(team_needs)"
    )


def test_team_route_supplies_shared_summary_and_detail_payloads():
    text = Path("owner_operations.py").read_text(encoding="utf-8")
    start = text.index('@bp.route("/team")')
    end = text.index('@bp.route("/lineup")', start)
    segment = text[start:end]

    assert "needs=needs" in segment
    assert "team_needs=team_needs" in segment
    assert "team_accuracy=team_accuracy" in segment


def test_team_route_builds_summary_once_from_the_shared_result():
    text = Path("owner_operations.py").read_text(encoding="utf-8")
    start = text.index('@bp.route("/team")')
    end = text.index('@bp.route("/lineup")', start)
    segment = text[start:end]

    assert segment.count("build_team_needs_summary(team_needs)") == 1
