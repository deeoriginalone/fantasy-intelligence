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


def test_command_center_surfaces_supported_summary_links():
    text=Path("templates/dashboard.html").read_text()
    for label in ("League Overview", "Start/Sit", "Waivers", "Trades", "Survivor", "NFL Highlights", "What Changed", "Risk Alerts"):
        assert label in text
    assert "owner_ops.waivers_page" in text
    assert "owner_ops.trades_page" in text
    assert "nfl_intelligence.home" in text
    assert "{% set decision_center = none %}" in text
    assert text.count('id="command-center-title"') == 1
    assert "Evidence and diagnostics" in text


def test_command_center_context_uses_existing_dashboard_fields():
    text=Path("templates/dashboard.html").read_text()
    for label in ("Teams", "Format", "Season", "Draft", "Freshness", "Status"):
        assert f"<dt>{label}</dt>" in text
    assert "league_overview.draft_type" in text
    assert "league_overview.draft_status" in text


def test_command_center_reuses_league_overview_facts():
    text=Path("templates/dashboard.html").read_text()
    for label in ("My Team", "Record", "Format", "Draft Slot", "Playoff Teams", "FAAB Budget"):
        assert f"<dt>{label}</dt>" in text
    assert "league_overview.teams" in text
    assert "overview_owner" in text
    assert "league-identity" in text
    assert "League identity" in text


def test_navigation_groups_preserve_core_and_supporting_destinations():
    text=Path("templates/base.html").read_text()
    for label in ("Season Planning", "Admin", "Command Center", "My Team", "Waivers", "Trades", "Survivor", "NFL Intelligence", "Team Changes", "Draft Board", "Mock Draft", "Sleeper Hub", "Diagnostics"):
        assert label in text
    assert ">Primary<" not in text
    assert "Market Intelligence" not in text
    assert "League Overview" not in text


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
