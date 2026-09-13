from pathlib import Path


def test_team_needs_summary_uses_jinja_namespace_and_actionable_detail():
    text = Path("templates/_team_needs_summary.html").read_text(encoding="utf-8")
    assert "namespace(actionable=[])" in text
    assert "ns.actionable" in text
    assert "ADD_DEPTH" in text


def test_shared_health_outage_does_not_render_empty_card_disclosure():
    text = Path("templates/_team_recommendations.html").read_text(encoding="utf-8")
    assert "player.health_shared_only" in text
    assert "Evidence issue" in text


def test_print_hides_navigation_and_closed_diagnostics():
    text = Path("templates/team.html").read_text(encoding="utf-8")
    assert "@media print" in text
    assert ".topbar{display:none!important}" in text
    assert ".diagnostic-details:not([open])" in text
    assert ".ux-completion-panel{display:none!important}" in text


def test_team_needs_and_bench_use_progressive_disclosure():
    needs = Path("templates/_team_needs_summary.html").read_text(encoding="utf-8")
    bench = Path("templates/_team_bench_plan.html").read_text(encoding="utf-8")
    assert "<details>" in needs and "All seven position needs" in needs
    assert "<details>" in bench and "Slot-by-slot contingency detail" in bench
