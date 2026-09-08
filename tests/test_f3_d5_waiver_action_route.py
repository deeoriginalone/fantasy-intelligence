from flask import Flask
from jinja2 import DictLoader

from sleeper_intelligence_routes import (
    create_sleeper_intelligence_blueprint,
)


class Cursor:
    def close(self):
        pass


class Connection:
    def cursor(self):
        return Cursor()

    def close(self):
        pass


def build_test_app(monkeypatch):
    monkeypatch.setattr(
        "sleeper_intelligence_routes.build",
        lambda *args: {
            "waiver_candidates": [],
            "waiver_action_plans": [],
            "local_roster_context": {},
        },
    )

    app = Flask(__name__)

    app.jinja_loader = DictLoader(
        {
            "sleeper_intelligence.html": """
            {% include "_waiver_action_publication.html" %}
            """,
            "_waiver_action_publication.html": """
            {% if not waiver_publication.allowed %}
            Publication blocked.
            {{ waiver_publication.decision.reason_codes|join(', ') }}
            {% endif %}
            """,
        }
    )

    app.config["SLEEPER_LEAGUE_ID"] = "league"

    app.register_blueprint(
        create_sleeper_intelligence_blueprint(
            lambda: Connection()
        )
    )

    return app


def test_html_route_fails_closed_when_readiness_path_missing(
    monkeypatch,):
    monkeypatch.delenv(
        "F3_READINESS_REPORT_PATH",
        raising=False,
    )
    app = build_test_app(monkeypatch)

    response = app.test_client().get(
        "/sleeper-intelligence/"
    )

    assert response.status_code == 200
    assert b"Publication blocked" in response.data
    assert b"READINESS_REPORT_PATH_MISSING" in response.data


def test_json_contract_remains_unchanged(monkeypatch):
    payload = {
        "waiver_candidates": [{"name": "A"}],
        "waiver_action_plans": [],
        "local_roster_context": {},
    }

    monkeypatch.setattr(
        "sleeper_intelligence_routes.build",
        lambda *args: payload,
    )

    app = Flask(__name__)
    app.config["SLEEPER_LEAGUE_ID"] = "league"

    app.register_blueprint(
        create_sleeper_intelligence_blueprint(
            lambda: Connection()
        )
    )

    response = app.test_client().get(
        "/sleeper-intelligence/json"
    )

    assert response.status_code == 200
    assert response.get_json() == payload