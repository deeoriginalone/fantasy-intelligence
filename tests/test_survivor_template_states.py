from pathlib import Path

import pytest
from flask import Flask, render_template
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader


def base_context(**overrides):
    ctx = {
        "survivor_season": 2026,
        "survivor_week": 1,
        "pool_key": "default",
        "strategy": "balanced",
        "used_teams": ["JAX"],
        "candidates": [],
        "survivor_summary": {"primary": None, "fallbacks": [], "avoid": [], "save_for_later": [],
                              "risks": [], "multi_week_roadmap": {"state": "UNAVAILABLE",
                              "reason": "SURVIVOR_MULTI_WEEK_MODEL_UNAVAILABLE",
                              "explanation": "No supported multi-week survivor optimizer exists yet."}},
        "survivor_status": {"season": 2026, "active_week": 1, "history_status": "verified", "week_state": "PENDING_RESULT",
                             "used_team_count": 1, "remaining_team_count": 31,
                             "evidence_state": "UNAVAILABLE", "freshness_state": "UNAVAILABLE",
                             "blocker_reason": None, "degrade_reason": None, "last_verified": None,
                             "state": "PENDING_RESULT"},
        "survivor_history": [{"week": 1, "team": "JAX", "status": "pending", "pool_key": "default",
                               "season": 2026, "model_probability": None, "survivor_score": None}],
        "existing_selection": {"team": "JAX", "status": "pending"},
        "result_label": "Pending",
        "next_week": 2,
        "last_verified_pacific": None,
    }
    ctx.update(overrides)
    return ctx



@pytest.fixture
def app():
    templates_dir = str(Path(__file__).resolve().parents[1] / "templates")
    app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]), template_folder=templates_dir)
    app.config.update(TESTING=True, SECRET_KEY="test")
    app.jinja_loader = ChoiceLoader([
        DictLoader({"base.html": "{% block content %}{% endblock %}"}),
        FileSystemLoader(templates_dir),
    ])
    app.jinja_env.globals["csrf_token"] = lambda: "test-csrf-token"

    @app.get("/survivor-test")
    def survivor_test_route():
        return render_template("survivor_intelligence.html", **app.extensions["survivor_test_context"])

    @app.post("/survivor-test/select")
    def select_stub():
        return "", 204

    @app.post("/survivor-test/status")
    def status_stub():
        return "", 204

    app.add_url_rule("/survivor-test/select", endpoint="survivor.select", view_func=select_stub)
    app.add_url_rule("/survivor-test/status", endpoint="survivor.status", view_func=status_stub)
    app.add_url_rule("/survivor-test", endpoint="survivor.home", view_func=survivor_test_route)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def render(app, client, **overrides):
    app.extensions["survivor_test_context"] = base_context(**overrides)
    return client.get("/survivor-test")


def test_page_returns_200(app, client):
    assert render(app, client).status_code == 200


def test_jax_visible_under_used_teams_and_history(app, client):
    html = render(app, client).get_data(as_text=True)
    assert "Week 1: JAX" in html
    assert "Result: pending" in html


def test_used_team_status_is_not_color_only(app, client):
    html = render(app, client).get_data(as_text=True)
    assert "Result: pending" in html


def test_hero_appears_before_rankings_and_lineage(app, client):
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "UNAVAILABLE"}
    html = render(app, client, survivor_status=status).get_data(as_text=True)
    assert html.index("SURVIVOR STATUS") < html.index("Full eligible rankings")
    assert html.index("SURVIVOR STATUS") < html.index("Data quality and lineage")


def test_full_rankings_collapsed_by_default(app, client):
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "UNAVAILABLE"}
    html = render(app, client, survivor_status=status).get_data(as_text=True)
    assert '<details class="sv-rankings">' in html
    assert "<summary>Full eligible rankings</summary>" in html


def test_metric_explanations_collapsed_by_default(app, client):
    html = render(app, client).get_data(as_text=True)
    assert '<details class="sv-metrics">' in html


def test_lineage_collapsed_and_last(app, client):
    html = render(app, client).get_data(as_text=True)
    assert html.rfind("sv-lineage") > html.rfind("sv-rankings")


def test_unavailable_state_renders_required_explanation(app, client):
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "UNAVAILABLE",
              "blocker_reason": "SURVIVOR_WEEK_EVIDENCE_MISSING"}
    html = render(app, client, survivor_status=status).get_data(as_text=True)
    assert "SURVIVOR RECOMMENDATION UNAVAILABLE" in html
    assert "confirmed used and excluded" in html


def test_unavailable_state_shows_refresh_button_with_csrf_token(app, client):
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "UNAVAILABLE",
              "blocker_reason": "SURVIVOR_WEEK_EVIDENCE_MISSING"}
    html = render(app, client, survivor_status=status).get_data(as_text=True)
    assert 'id="sv-refresh-btn"' in html
    assert "Refresh Market Intelligence for Week 1" in html
    assert "svCsrfToken=" in html
    assert "test-csrf-token" in html
    assert "/api/market-intelligence/refresh" in html


def test_refresh_button_absent_when_recommendation_is_ready(app, client):
    primary = {"team": "NE", "opponent": "SEA", "home_away": "HOME", "current_probability": 0.71,
               "stability_available": True, "stability": 0.9, "future_available": False, "future_value": None,
               "survivor_score": 0.7, "survivor_score_basis": "current_stability_only",
               "reason": "high current-week win probability"}
    summary = {**base_context()["survivor_summary"], "primary": primary, "fallbacks": []}
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "READY", "blocker_reason": None}
    html = render(app, client, survivor_summary=summary, survivor_status=status).get_data(as_text=True)
    assert 'id="sv-refresh-btn"' not in html


def test_blocked_history_state_renders_required_alert(app, client):
    status = base_context()["survivor_status"]
    status = {**status, "history_status": "read_failed", "state": "BLOCKED", "blocker_reason": "SURVIVOR_HISTORY_READ_FAILED"}
    html = render(app, client, survivor_status=status, survivor_history=[]).get_data(as_text=True)
    assert "ELIGIBILITY BLOCKED" in html
    assert "no survivor recommendation is being published" in html


def test_locked_week_shows_recorded_selection_not_another_pick(app, client):
    html = render(app, client).get_data(as_text=True)
    assert "WEEK 1 SELECTION RECORDED" in html
    assert "PICK THIS WEEK" not in html
    assert "Record " not in html
    assert "already recorded" in html


def test_locked_week_shows_next_week_link_when_verified(app, client):
    html = render(app, client).get_data(as_text=True)
    assert "View Week 2" in html


def test_locked_week_shows_unavailable_next_week_when_not_verified(app, client):
    html = render(app, client, next_week=None).get_data(as_text=True)
    assert "NEXT WEEK UNAVAILABLE" in html


def test_completed_week_shows_result(app, client):
    status = {**base_context()["survivor_status"], "week_state": "COMPLETED", "state": "COMPLETED"}
    html = render(app, client, survivor_status=status, existing_selection={"team": "JAX", "status": "won"}, result_label="Win").get_data(as_text=True)
    assert "Result: Win" in html
    assert "PICK THIS WEEK" not in html


def test_locked_week_rankings_labeled_model_snapshot_non_actionable(app, client):
    html = render(app, client).get_data(as_text=True)
    assert "Model snapshot for Week 1 (non-actionable)" in html
    assert "MODEL SNAPSHOT FOR WEEK 1" in html
    assert "Full eligible rankings" not in html


def test_ready_state_shows_primary_pick_and_no_neutral_fallback(app, client):
    primary = {"team": "NE", "opponent": "SEA", "home_away": "HOME", "current_probability": 0.71,
               "stability_available": True, "stability": 0.9, "future_available": False, "future_value": None,
               "survivor_score": 0.7, "survivor_score_basis": "current_stability_only",
               "reason": "high current-week win probability; future opportunity cost is unavailable (no supported future schedule evidence)"}
    summary = base_context()["survivor_summary"]
    summary = {**summary, "primary": primary, "fallbacks": []}
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "READY", "blocker_reason": None}
    html = render(app, client, survivor_summary=summary, survivor_status=status).get_data(as_text=True)
    assert "PICK THIS WEEK" in html
    assert "NE vs SEA" in html
    assert "50.0%" not in html


def test_completed_week_loss_shows_result(app, client):
    status = {**base_context()["survivor_status"], "week_state": "COMPLETED", "state": "COMPLETED"}
    html = render(app, client, survivor_status=status, existing_selection={"team": "JAX", "status": "lost"}, result_label="Loss").get_data(as_text=True)
    assert "Result: Loss" in html
    assert "PICK THIS WEEK" not in html


def test_stale_evidence_state_renders_unavailable_block_not_a_pick(app, client):
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "BLOCKED",
              "blocker_reason": "SURVIVOR_EVIDENCE_STALE", "evidence_state": "STALE", "freshness_state": "STALE"}
    html = render(app, client, survivor_status=status).get_data(as_text=True)
    assert "SURVIVOR RECOMMENDATION UNAVAILABLE" in html
    assert "SURVIVOR_EVIDENCE_STALE" in html
    assert "PICK THIS WEEK" not in html


def test_degraded_state_still_shows_a_disclosed_primary_pick(app, client):
    primary = {"team": "NE", "opponent": "SEA", "home_away": "HOME", "current_probability": 0.71,
               "stability_available": True, "stability": 0.9, "future_available": False, "future_value": None,
               "survivor_score": 0.7, "survivor_score_basis": "current_stability_only",
               "reason": "high current-week win probability; future opportunity cost is unavailable (no supported future schedule evidence)"}
    summary = {**base_context()["survivor_summary"], "primary": primary, "fallbacks": []}
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "DEGRADED",
              "degrade_reason": "SURVIVOR_FUTURE_VALUE_UNAVAILABLE", "blocker_reason": None}
    html = render(app, client, survivor_summary=summary, survivor_status=status).get_data(as_text=True)
    assert "PICK THIS WEEK" in html
    assert "DEGRADED" in html
    assert "SURVIVOR_FUTURE_VALUE_UNAVAILABLE" in html


def test_missing_evidence_agreement_shows_unavailable_not_a_number(app, client):
    primary = {"team": "NE", "opponent": "SEA", "home_away": "HOME", "current_probability": 0.71,
               "stability_available": False, "stability": None, "future_available": False, "future_value": None,
               "survivor_score": 0.71, "survivor_score_basis": "current_only",
               "reason": "high current-week win probability; evidence agreement is unavailable (missing model component)"}
    summary = {**base_context()["survivor_summary"], "primary": primary, "fallbacks": []}
    status = {**base_context()["survivor_status"], "week_state": "OPEN", "state": "DEGRADED", "blocker_reason": None}
    html = render(app, client, survivor_summary=summary, survivor_status=status).get_data(as_text=True)
    assert "Evidence agreement score (not a win probability): Unavailable" in html
