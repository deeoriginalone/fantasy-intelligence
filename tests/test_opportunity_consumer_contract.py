from pathlib import Path

from services.opportunity_evidence import build_opportunity_view


METRICS = ("snap_share", "route_participation", "target_share", "rush_share", "red_zone_share", "goal_line_share", "role_stability")


def period(offset=0.0):
    return {"values": {metric: 0.2 + offset for metric in METRICS}, "source": "official usage source", "source_recorded_at": "2026-09-15T10:00:00+00:00", "retrieved_at": "2026-09-15T12:00:00+00:00", "age": 60, "freshness_state": "FRESH", "completeness_state": "COMPLETE"}


def test_manager_view_is_informational_and_exposes_changes():
    view = build_opportunity_view({"current": period(0.1), "previous": period(), "rolling_baseline": period(-0.05)})
    assert view["current"]["authoritative"] is True
    assert view["what_changed"]["state"] == "AVAILABLE"
    assert view["decision_effect"] == "NONE"
    assert all("matchup_rank" not in item and "matchup_modifier" not in item for item in view["what_changed"]["changes"])


def test_templates_include_opportunity_evidence_without_conclusions():
    for name in ("templates/team.html", "templates/waivers.html", "templates/trades.html"):
        assert "_opportunity_evidence.html" in Path(name).read_text(encoding="utf-8")
    text = Path("templates/_opportunity_evidence.html").read_text(encoding="utf-8")
    for phrase in ("Target Share", "Snap Share", "Routes Run", "Red-Zone Usage", "Role Stability", "Informational evidence only"):
        assert phrase in text
    for phrase in ("BREAKOUT", "REGRESSION", "BUY LOW", "SELL HIGH", "SLEEPER", "LEAGUE WINNER"):
        assert phrase not in text