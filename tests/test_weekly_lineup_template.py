from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def test_template_renders_decisions_and_has_no_form():
    templates = Path(__file__).resolve().parents[1] / "templates"

    env = Environment(
        loader=FileSystemLoader(templates)
    )

    env.globals["url_for"] = (
        lambda endpoint, filename=None, **kwargs:
        f"/static/{filename}" if filename else "/"
    )

    html = env.get_template("lineup.html").render(
        context={"mode": "LIVE"},
        meta={"team_name": "Mine"},
        lineup_intelligence={
            "blockers": [],
            "missing_evidence_players": [],
            "weekly_total": 100.5,
            "vacancies": [],
            "methodology": "No lineup is submitted.",
            "start_sit_decisions": [
                {
                    "decision": "START",
                    "slot": "QB",
                    "start": {"player": "A"},
                    "sit": {"player": "B"},
                    "weekly_score_delta": 2,
                    "confidence": {
                        "label": "HIGH",
                        "score": 100,
                    },
                    "reason": "A ahead",
                }
            ],
            "starters": [
                {
                    "slot": "QB",
                    "player": "A",
                    "is_bye": False,
                    "opponent": "X",
                    "weekly_baseline": 20,
                    "matchup_modifier": 0,
                    "injury_status": "Healthy",
                    "weekly_score": 20,
                    "confidence": {
                        "label": "HIGH",
                        "score": 100,
                    },
                    "reason": "Evidence",
                }
            ],
            "bench": [],
        },
    )

    assert "Weekly Lineup Intelligence" in html
    assert "Start/Sit Decisions" in html
    assert "A" in html
    assert "B" in html
    assert "HIGH 100%" in html
    assert "100.50" in html
    assert "HOLD" not in html

    assert "<form" not in html
    # submit text allowed because page says 'does not submit a lineup'


def test_template_renders_without_optional_lineage_global():
    templates = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(templates))
    env.globals["url_for"] = lambda endpoint, filename=None, **kwargs: "/"
    html = env.get_template("lineup.html").render(
        context={"mode": "LIVE"},
        meta={"team_name": "Mine"},
        lineup_intelligence={
            "blockers": [], "missing_evidence_players": [], "weekly_total": 0,
            "vacancies": [], "methodology": "No lineup is submitted.",
            "start_sit_decisions": [], "starters": [], "bench": [],
            "integrity": {"confidence": {"label": "UNKNOWN", "score": 0}, "blockers": [], "freshness": {"domains": {}}},
        },
    )
    assert "UNKNOWN: No verified page evidence was supplied." in html
