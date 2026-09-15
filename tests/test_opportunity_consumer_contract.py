from pathlib import Path

from services.opportunity_evidence import build_opportunity_view


METRICS = ("snap_share", "route_participation", "target_share", "rush_share", "red_zone_share", "goal_line_share", "role_stability")


def period(offset=0.0):
    return {"values": {metric: 0.2 + offset for metric in METRICS}, "source": "official usage source", "source_recorded_at": "2026-09-15T10:00:00+00:00", "retrieved_at": "2026-09-15T12:00:00+00:00", "age": 60, "freshness_state": "FRESH", "completeness_state": "COMPLETE"}


def test_manager_view_is_informational_and_exposes_changes():
    view = build_opportunity_view({
        "current": period(0.1), "previous": period(), "rolling_baseline": period(-0.05),
        "market_value": {
            "market_value_state": "VALUE_STABLE", "source": "supported market source",
            "source_recorded_at": "2026-09-15T10:00:00+00:00", "retrieved_at": "2026-09-15T12:00:00+00:00",
            "freshness_state": "FRESH", "completeness_state": "COMPLETE",
        },
    })
    assert view["current"]["authoritative"] is True
    assert view["what_changed"]["state"] == "AVAILABLE"
    assert view["classification"]["state"] == "GROWING_OPPORTUNITY"
    assert view["market_value"]["market_value_state"] == "VALUE_STABLE"
    assert view["market_value"]["authoritative"] is True
    assert view["market_signal"]["market_signal_state"] == "FAIR_VALUE_SIGNAL"
    assert view["market_signal"]["authoritative"] is True
    assert view["decision_effect"] == "NONE"
    assert all("matchup_rank" not in item and "matchup_modifier" not in item for item in view["what_changed"]["changes"])


def test_templates_include_opportunity_evidence_without_conclusions():
    for name in ("templates/team.html", "templates/waivers.html", "templates/trades.html"):
        assert "_opportunity_evidence.html" in Path(name).read_text(encoding="utf-8")
    text = Path("templates/_opportunity_evidence.html").read_text(encoding="utf-8")
    for phrase in ("Target Share", "Snap Share", "Routes Run", "Red-Zone Usage", "Role Stability", "Market Value Evidence", "Market Signal Evidence", "Informational evidence only"):
        assert phrase in text
    for phrase in ("BREAKOUT", "REGRESSION", "BUY LOW", "SELL HIGH", "SLEEPER", "LEAGUE WINNER", "MUST ADD", "MUST TRADE"):
        assert phrase not in text