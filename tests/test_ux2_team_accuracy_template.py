from pathlib import Path

def test_team_template_wires_accuracy_partial():
    text=Path("templates/team.html").read_text(encoding="utf-8")
    assert '{% include "_team_accuracy.html" %}' in text
    assert text.index('{% include "_team_recommendations.html" %}') < text.index('{% include "_team_accuracy.html" %}')

def test_accuracy_partial_explains_required_domains():
    text=Path("templates/_team_accuracy.html").read_text(encoding="utf-8")
    for phrase in ("League and Scoring Settings","Starter Matchup Evidence","Displayed Metric Guidance"):
        assert phrase in text
    assert '{% include "_team_health.html" %}' in text


def test_team_template_removes_unsupported_aggregate_metrics():
    text=Path("templates/team.html").read_text(encoding="utf-8")
    assert "WEEKLY STARTER SCORE" not in text
    assert "{{ overall }} · {{ roster_score }}" not in text


def test_team_template_distinguishes_unavailable_weekly_score_from_zero():
    text=Path("templates/_team_recommendations.html").read_text(encoding="utf-8")
    assert "weekly_value_state" in text
    assert "player.weekly_score is not none" in text
    assert "weekly_score or 0" not in text


def test_team_template_renders_explanation_fields():
    text=Path("templates/_team_recommendations.html").read_text(encoding="utf-8")
    for phrase in ("Recommendation confidence:","Why:","Evidence issue"):
        assert phrase in text
    assert "player.confidence.label" in text
    assert "player.reason" in text
    assert "player.evidence_gaps" in text


def test_matchup_rank_contract_is_complete():
    text=Path("docs/METRIC_DEFINITIONS.md").read_text(encoding="utf-8")
    section=text.split("## Matchup Rank",1)[1].split("## Roster Strength",1)[0]
    for field in ("Name:","Purpose:","Scale or unit:","Inputs:","Directionality:","Freshness requirement:","Missing-data behavior:","Decision use:","Owner service or contract:","Validation tests:"):
        assert field in section

def test_team_needs_table_shows_reconciled_dimensions():
    text = Path("templates/_team_needs_cards.html").read_text(encoding="utf-8")

    for phrase in (
        "Starter Coverage",
        "Required Starters",
        "Rostered / Eligible",
        "Depth Target",
        "Depth Status",
        "Strategic Need",
        "Driver",
    ):
        assert phrase in text

    for field in ("item.starter_coverage", "item.depth_status", "item.depth_target", "item.strategic_need", "item.drivers"):
        assert field in text
