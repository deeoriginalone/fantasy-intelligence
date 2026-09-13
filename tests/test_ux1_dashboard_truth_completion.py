from pathlib import Path
from services.ux_evidence import dashboard_agreement_evidence, dashboard_state_contract, format_pacific_datetime, shared_league_facts

def test_pacific_timestamp():
    assert format_pacific_datetime(0).endswith(("PST", "PDT"))

def test_invalid_timestamp_fails_closed():
    item=dashboard_state_contract({}, {"start_time":"bad"})["draft_start_time"]
    assert item["state"]=="UNKNOWN"
    assert item["blocker"]=="DRAFT_START_TIME_INVALID"

def test_agreement_pass_and_block():
    assert dashboard_agreement_evidence({"season":"2026"},{"season":"2026"})["state"]=="AVAILABLE"
    assert dashboard_agreement_evidence({"season":"2026"},{"season":"2025"})["state"]=="BLOCKED"

def test_agreement_unknown_without_overlap():
    assert dashboard_agreement_evidence({"season":"2026"})["state"]=="UNKNOWN"

def test_template_surfaces():
    text=Path("templates/dashboard.html").read_text()
    assert "data-dashboard-freshness" in text
    assert "data-dashboard-agreement" in text
    assert "Data last checked" in text


def test_shared_league_facts_available_and_fail_closed():
    available=shared_league_facts({"season":"2026","status":"in_season"})
    assert available["season"]["state"]=="AVAILABLE"
    assert available["league_status"]["value"]=="in_season"
    blocked=shared_league_facts({},blocker="LEAGUE_SOURCE_UNAVAILABLE")
    assert blocked["season"]["state"]=="UNKNOWN"
    assert blocked["league_status"]["blocker"]=="LEAGUE_SOURCE_UNAVAILABLE"

def test_shared_league_facts_support_three_page_agreement():
    league={"season":"2026","status":"in_season"}
    result=dashboard_agreement_evidence(shared_league_facts(league),shared_league_facts(league),shared_league_facts(league))
    assert result["state"]=="AVAILABLE"
    assert result["checked_fields"]==["league_status","season"]

def test_active_route_source_wiring_is_present():
    app_text=Path("app.py").read_text()
    owner_text=Path("owner_operations.py").read_text()
    assert 'dashboard_evidence["shared_facts"] = dashboard_shared_facts' in app_text
    assert 'my_team_facts=shared_league_facts(league_source, blocker=league_error)' in app_text
    assert 'command_center_facts=shared_league_facts(league_source, blocker=league_error)' in app_text
    assert '"shared_facts": shared_league_facts(league)' in owner_text
    assert 'blocker="LIVE_LEAGUE_FACTS_NOT_APPLICABLE"' in owner_text
    assert '@bp.route("/team")' in owner_text
    assert '@bp.route("/gm")' in owner_text
