from pathlib import Path
from services.ux_evidence import dashboard_agreement_evidence, dashboard_state_contract, format_pacific_datetime

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
