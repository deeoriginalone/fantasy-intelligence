from pathlib import Path

from flask import Flask

import nfl_intelligence_routes
import survivor_routes


ROOT = Path(__file__).resolve().parents[1]


def blocked_week(_season):
    return {"authoritative": False, "state": "CONFLICTING_OWNER", "blockers": ["CONFLICTING_WEEK_OWNERS"]}


def make_app(monkeypatch):
    app = Flask(__name__, template_folder=str(ROOT / "templates"))
    app.config["SECRET_KEY"] = "test"
    app.config["WEEK_AUTHORITY_ACQUIRER"] = blocked_week
    app.context_processor(lambda: {"csrf_token": lambda: "test-csrf"})
    endpoint_names = (
        "dashboard", "draftboard", "draft_accuracy.home", "draft_health.home",
        "predraft", "mock_draft_lab", "season_sandbox.sandbox_home",
        "owner_ops.team_page", "owner_ops.lineup_page", "owner_ops.waivers_page",
        "owner_ops.trades_page", "owner_ops.gm_page", "sleeper_hub.home",
        "sleeper_intelligence.home", "market_intelligence.home", "league_manager",
        "track_draft", "imports", "agents", "sleeper_teams", "draftcenter",
    )
    for index, endpoint in enumerate(endpoint_names):
        app.add_url_rule(f"/__test_{index}", endpoint=endpoint, view_func=lambda: "")
    monkeypatch.setattr(nfl_intelligence_routes, "available_weeks", lambda season: [])
    app.register_blueprint(survivor_routes.survivor_bp)
    app.register_blueprint(nfl_intelligence_routes.nfl_intelligence_bp)
    return app


def test_survivor_current_week_conflict_renders_fail_closed_page(monkeypatch):
    response = make_app(monkeypatch).test_client().get("/survivor")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "SURVIVOR STATUS" in body
    assert "UNAVAILABLE" in body
    assert "CONFLICTING_WEEK_OWNERS" in body


def test_nfl_current_week_conflict_renders_insufficient_evidence_page(monkeypatch):
    response = make_app(monkeypatch).test_client().get("/nfl-intelligence")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "NFL Intelligence" in body
    assert "UNAVAILABLE" in body
    assert "No prediction or recommendation is published." in body


def test_explicit_week_remains_supported_for_both_routes(monkeypatch):
    app = make_app(monkeypatch)
    client = app.test_client()
    assert client.get("/survivor?season=2026&week=1").status_code == 200
    assert client.get("/nfl-intelligence?season=2026&week=1").status_code == 200