from datetime import datetime
from types import SimpleNamespace
from services.waiver_action_publication import build_waiver_publication


def report(allowed):
    level=SimpleNamespace(name="READY" if allowed else "BLOCKED")
    return SimpleNamespace(
        components={}, issues=(), publish_allowed=allowed,
        overall_status="READY" if allowed else "BLOCKED",
        generated_at=datetime.fromisoformat("2026-09-04T08:00:00+00:00"),
    )


def intel():
    return {"waiver_candidates":[{"name":"Add RB"}],"waiver_action_plans":[{
        "priority":1,"add":{"name":"Add RB","position":"RB","reason":"RB need"},
        "drop":{"player_name":"Bench WR","position":"WR"},"recommended_bid_pct":12,
        "recommended_bid":None,"urgency":"HIGH","summary":"Add Add RB and drop Bench WR"}],
        "local_roster_context":{"bench_count":2}}


def test_blocked_report_fails_closed():
    result=build_waiver_publication(intel(),report(False))
    assert result["allowed"] is False
    assert result["waiver_action_plans"] == []


def test_ready_report_publishes_existing_contract():
    result=build_waiver_publication(intel(),report(True))
    assert result["allowed"] is True
    assert result["waiver_action_plans"][0]["add"]["name"] == "Add RB"


def test_unknown_budget_does_not_publish_unit_bid():
    result=build_waiver_publication(intel(),report(True))
    assert "recommended_bid" not in result["waiver_action_plans"][0]


def test_explicit_starter_drop_is_rejected():
    data=intel();data["waiver_action_plans"][0]["drop"]["is_starter"]=True
    result=build_waiver_publication(data,report(True))
    assert result["waiver_action_plans"] == []
