from pathlib import Path

def test_team_route_builds_and_supplies_accuracy_contract():
    text=Path("owner_operations.py").read_text(encoding="utf-8")
    start=text.index('@bp.route("/team")'); end=text.index('@bp.route("/lineup")',start); segment=text[start:end]
    for expected in ("build_team_accuracy_contract","team_accuracy=team_accuracy","league_settings=league_settings","team_needs=team_needs","team_health=team_health"):
        assert expected in segment
