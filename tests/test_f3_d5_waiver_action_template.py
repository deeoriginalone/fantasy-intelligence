from pathlib import Path
from jinja2 import Environment,FileSystemLoader


def render(publication):
    templates=Path(__file__).resolve().parents[1]/"templates"
    return Environment(loader=FileSystemLoader(templates)).get_template("_waiver_action_publication.html").render(waiver_publication=publication)


def test_blocked_state_renders_reason():
    html=render({"allowed":False,"decision":{"reason_codes":["READINESS_REPORT_PATH_MISSING"]}})
    assert "Publication blocked" in html
    assert "READINESS_REPORT_PATH_MISSING" in html


def test_plan_renders_f3_d4_fields_without_unknown_bid():
    html=render({"allowed":True,"local_roster_context":{"bench_count":2},"waiver_action_plans":[{
        "priority":1,"summary":"Add A and drop B","add":{"name":"A","position":"RB","team":"LV","reason":"RB need"},
        "drop":{"player_name":"B","position":"WR"},"urgency":"HIGH","recommended_bid_pct":12}]})
    for text in ("A","B","HIGH","12%","RB need"):
        assert text in html
    assert "Recommended bid:</strong>" not in html
