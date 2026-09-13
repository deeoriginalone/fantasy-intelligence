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
    return app


@pytest.fixture
def render_team_health(app):
    def _render(payload):
        with app.app_context():
            return render_template("_team_health.html", team_health=payload)
    return _render


@pytest.fixture
def available_health():
    return {
        "state": "AVAILABLE", "source": "Sleeper", "freshness_state": "FRESH",
        "healthy": 5, "questionable": 1, "doubtful": 0, "out": 1, "ir": 1,
        "unknown": 0, "blocker": None,
        "recommendation_impact": "Health data supports lineup recommendations.",
    }


@pytest.mark.parametrize("payload,assertion", DEFENSIVE_HEALTH_CASES)
def test_health_template_defensive_states(render_team_health, payload, assertion):
    html = render_team_health(payload)
    assertion(html, payload)


@pytest.mark.parametrize("freshness_state", UNKNOWN_FRESHNESS_CASES)
def test_health_template_unknown_freshness_renders_safe_fallback(render_team_health, available_health, freshness_state):
    payload = dict(available_health, freshness_state=freshness_state)
    html = render_team_health(payload)
    assert_unknown_state_rendered(html, payload)
    assert "cannot be treated as current" in html
    assert "Healthy</div>" not in html


def test_health_template_renders_metadata_and_unverified_freshness(render_team_health, available_health):
    html = render_team_health(available_health)
    assert "Source:</strong> Sleeper" in html
    assert "<strong>Freshness:</strong>" in html
    assert "UNVERIFIED" in html
    assert "Last verified:</strong> Unavailable" in html
    assert "<strong>Age:</strong>" in html
    assert "Unavailable" in html
    assert "Health data supports lineup recommendations." in html


def test_health_template_renders_supplied_metadata(render_team_health, available_health):
    payload = dict(available_health, last_verified="2026-09-12T12:00:00+00:00", age=3600)
    html = render_team_health(payload)
    assert "Freshness:</strong> FRESH" in html
    assert "Last verified:</strong> 2026-09-12T12:00:00+00:00" in html
    assert "Age:</strong> 3600" in html
