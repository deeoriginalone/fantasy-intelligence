import pytest
from pathlib import Path
from flask import Flask, render_template

from tests.helpers.health_assertions import assert_unknown_state_rendered
from tests.helpers.health_test_cases import DEFENSIVE_HEALTH_CASES, UNKNOWN_FRESHNESS_CASES


@pytest.fixture
def app():
    app = Flask(
        __name__,
        root_path=str(Path(__file__).resolve().parents[1]),
        template_folder="templates",
    )
    app.config.update(TESTING=True)
    app.extensions["team_health_test_payload"] = None

    @app.get("/team-health-test")
    def team_health_test_route():
        return render_template(
            "_team_health.html",
            team_health=app.extensions["team_health_test_payload"],
        )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def get_team_health_page(app, client):
    def _get(payload):
        app.extensions["team_health_test_payload"] = payload
        return client.get("/team-health-test")
    return _get


@pytest.fixture
def team_route_payload():
    return {
        "state": "AVAILABLE", "source": "Sleeper", "freshness_state": "FRESH",
        "healthy": 5, "questionable": 1, "doubtful": 0, "out": 1, "ir": 1,
        "unknown": 0, "blocker": None,
        "recommendation_impact": "Health data supports lineup recommendations.",
    }


@pytest.mark.parametrize("payload,assertion", DEFENSIVE_HEALTH_CASES)
def test_team_health_route_defensive_states(get_team_health_page, payload, assertion):
    response = get_team_health_page(payload)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assertion(html, payload)


@pytest.mark.parametrize("freshness_state", UNKNOWN_FRESHNESS_CASES)
def test_team_health_route_unknown_freshness_renders_safe_fallback(get_team_health_page, team_route_payload, freshness_state):
    payload = dict(team_route_payload, freshness_state=freshness_state)
    response = get_team_health_page(payload)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert_unknown_state_rendered(html, payload)
    assert "cannot be treated as current" in html
    assert "Healthy</div>" not in html
