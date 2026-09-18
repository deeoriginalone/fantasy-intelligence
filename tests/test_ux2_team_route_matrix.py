from pathlib import Path

import pytest
from flask import Flask

import owner_operations
import services.weekly_lineup_intelligence as weekly_lineup_intelligence
from owner_operations import create_owner_operations_blueprint
from services.lineup_evidence import build_matchup_evidence


POSITIONS = ("QB", "RB", "RB", "WR", "WR", "TE", "WR", "K", "DEF")


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.value = None

    def execute(self, query, params=None):
        if "application_state" in query:
            self.value = None
        elif "FROM players" in query:
            key = str((params or [""])[0])
            self.value = self.rows.get(key)
        else:
            self.value = None

    def fetchone(self):
        value, self.value = self.value, None
        return value

    def fetchall(self):
        return []

    def close(self):
        pass


class Connection:
    def __init__(self, rows):
        self.rows = rows
        self.cursor_instance = Cursor(rows)

    def cursor(self):
        return self.cursor_instance

    def close(self):
        pass


def health_payload(state="AVAILABLE", freshness="FRESH", blocker=None, last_verified=None, age=None):
    return {
        "state": state,
        "source": "Controlled health fixture",
        "freshness_state": freshness,
        "last_verified": last_verified,
        "age": age,
        "healthy": 9 if state == "AVAILABLE" else None,
        "questionable": 0 if state == "AVAILABLE" else None,
        "doubtful": 0 if state == "AVAILABLE" else None,
        "out": 0 if state == "AVAILABLE" else None,
        "ir": 0 if state == "AVAILABLE" else None,
        "unknown": 0 if state == "AVAILABLE" else None,
        "blocker": blocker,
        "recommendation_impact": f"Controlled {state} health impact for the affected recommendation.",
    }


def make_app(monkeypatch, health, weekly_score=None, league_available=True, unknown_player=None, unknown_players=None, authoritative_matchup=False, matchup_overrides=None, no_needs=False, trade_partner=False, trade_enrichment=None, trade_scenario=None):
    unknown_players = set(unknown_players or ())
    names = [f"P{index}" for index in range(len(POSITIONS))]
    players = {}
    rows = {}
    for index, (name, position) in enumerate(zip(names, POSITIONS)):
        status = "Unknown" if name == unknown_player or name in unknown_players else "Healthy"
        players[str(index)] = {"full_name": name, "position": position, "team": "T", "injury_status": status}
        rows[name.lower().replace(" ", "")] = (
            name, position, "T", 20, 12.0, 2, 50.0, 8, status,
        )
    if trade_partner:
        players["partner"] = {"full_name": "Partner", "position": "WR", "team": "T", "injury_status": "Healthy"}
        rows["partner"] = ("Partner", "WR", "T", 20, 12.0, 2, 50.0, 8, "Healthy")

    def current_roster_rows(roster):
        output = []
        for index, player in enumerate(roster):
            row = dict(player)
            row.update({
                "slot": ("QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX", "K", "DEF")[index],
                "vacant": False,
                "is_bye": False,
                "opponent": "SF",
                "source_player_id": f"sleeper-{index}",
                "local_player_id": index,
                "matchup_rank": 10,
                "matchup_modifier": 0.1,
                "weekly_baseline": 10.0,
                "weekly_score": weekly_score,
                "injury_multiplier": 1.0,
                "confidence": {"label": "HIGH", "score": 90},
                "reason": "Controlled matchup evidence.",
                "evidence_gaps": [],
            })
            if authoritative_matchup:
                row.update({
                    "matchup_population": "ALL_DEFENSES_BY_POSITION",
                    "matchup_directionality": "LOWER_IS_HARDER",
                    "matchup_source": "automated:nflverse",
                    "matchup_source_authority": "automated",
                    "matchup_sample_threshold_id": "matchup.sample.v1",
                    "matchup_retrieved_at": "2999-01-01T00:00:00+00:00",
                })
            if matchup_overrides:
                row.update(matchup_overrides)
            row["lineup_evidence"] = {"matchup": build_matchup_evidence(row, season=2026, week=1)}
            if row.get("player") == unknown_player or row.get("player") in unknown_players:
                row["injury_status"] = "Unknown"
            output.append(row)
        return output, [], sum((weekly_score or 0) for _ in output), []

    monkeypatch.setattr(owner_operations, "enrich_players", trade_enrichment or (lambda cur, roster, week, **kwargs: roster))
    monkeypatch.setattr(owner_operations, "current_week", lambda cur: 1)
    monkeypatch.setattr(owner_operations, "optimize_lineup", current_roster_rows)
    monkeypatch.setattr(weekly_lineup_intelligence, "optimize_lineup", current_roster_rows)
    monkeypatch.setattr(owner_operations, "team_health_contract", lambda *args, **kwargs: health)
    if no_needs:
        monkeypatch.setattr(owner_operations, "team_needs_contract", lambda *args, **kwargs: {position: {"state": "AVAILABLE", "strategic_need": "NO_ACTION", "starter_coverage": "COVERED", "depth_status": "AT_TARGET", "depth_target": 1, "required_starters": 1, "rostered_or_eligible": 1, "drivers": ["Supported target satisfied."]} for position in ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")})

    league = {
        "name": "Controlled League",
        "roster_positions": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN"],
        "scoring_settings": {"rec": 1.0},
    } if league_available else {}
    connection = Connection(rows)
    blueprint = create_owner_operations_blueprint(
        lambda: connection,
        lambda league_id: league,
        lambda league_id: [{"user_id": "owner", "is_owner": True}, *([{"user_id": "partner", "display_name": "Partner"}] if trade_partner else [])],
        lambda league_id: [{"owner_id": "owner", "players": [key for key in players if key != "partner"]}, *([{"owner_id": "partner", "roster_id": 2, "players": ["partner"]}] if trade_partner else [])],
        lambda: players,
        lambda value: str(value).lower().replace(" ", ""),
    )
    app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]), template_folder="templates")
    app.config.update(TESTING=True, SLEEPER_LEAGUE_ID="controlled", TRADE_SCENARIO=trade_scenario)
    app.register_blueprint(blueprint)
    app.jinja_env.globals["url_for"] = lambda *args, **kwargs: "/"
    app.jinja_env.globals["ux_roster_lineage"] = lambda roster: []
    app.jinja_env.globals["ux_route_evidence"] = lambda *args: {"fields": {}}
    return app


@pytest.mark.parametrize(
    "health,expected",
    [
        (health_payload(last_verified="2026-09-12T12:00:00+00:00", age=60), "FRESH"),
        (health_payload(freshness="AGING", last_verified="2026-09-12T12:00:00+00:00", age=90000), "AGING"),
        (health_payload(state="STALE", freshness="STALE", blocker="TEAM_HEALTH_STALE"), "STALE"),
        (health_payload(state="UNAVAILABLE", freshness="UNAVAILABLE", blocker="TEAM_HEALTH_UNAVAILABLE"), "UNAVAILABLE"),
        (health_payload(state="BLOCKED", freshness="BLOCKED", blocker="HEALTH_REFRESH_FAILED"), "BLOCKED"),
        (health_payload(state="UNKNOWN", freshness="UNKNOWN", blocker="UNSUPPORTED_HEALTH_FRESHNESS_STATE"), "UNKNOWN"),
    ],
)
def test_active_team_route_health_matrix(monkeypatch, health, expected):
    response = make_app(monkeypatch, health).test_client().get("/team")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Next Best Team Action" in html
    assert "Expected fantasy impact" in html
    assert "Recommended Starting Lineup" in html
    assert "Why This Lineup Is Trusted" in html
    assert "Bench Priority" in html
    assert "Biggest Risks This Week" in html
    assert "Actionable Team Needs" in html
    assert "Roster Outlook" in html
    assert "Controlled health fixture" in html
    assert expected in html
    assert "Unavailable" in html
    assert "Controlled" in html
    assert "<details open" not in html


def test_active_team_route_unknown_player_health_targets_only_that_recommendation(monkeypatch):
    response = make_app(monkeypatch, health_payload(last_verified="2026-09-12T12:00:00+00:00", age=60), unknown_player="P0").test_client().get("/team")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "PLAYER_HEALTH_UNAVAILABLE" in html
    assert "MONITOR" in html
    assert "Healthy" in html


@pytest.mark.parametrize("weekly_score,expected_state,expected_value", [(12.0, "AVAILABLE", "12.00"), (0.0, "AVAILABLE", "0.00"), (None, "UNAVAILABLE", "Unavailable")])
def test_active_team_route_weekly_value_states(monkeypatch, weekly_score, expected_state, expected_value):
    response = make_app(monkeypatch, health_payload(last_verified="2026-09-12T12:00:00+00:00", age=60), weekly_score=weekly_score).test_client().get("/team")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert expected_state in html
    assert expected_value in html


def test_active_team_route_missing_league_settings_fails_closed(monkeypatch):
    response = make_app(monkeypatch, health_payload(state="UNAVAILABLE", freshness="UNAVAILABLE", blocker="TEAM_HEALTH_UNAVAILABLE"), league_available=False).test_client().get("/team")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "League settings unavailable" in html
    assert "Analysis unavailable" in html
    assert "Next Best Team Action" in html


def test_complete_evidence_route_is_not_blanket_monitor(monkeypatch):
    response = make_app(monkeypatch, health_payload(last_verified="2026-09-12T12:00:00+00:00", age=60), weekly_score=12.0, authoritative_matchup=True, no_needs=True).test_client().get("/team")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "START" in html
    assert "No urgent evidence-supported change" in html
    assert "90%" in html
    assert "Playoff readiness evidence is not supplied" in html


def test_multiple_monitored_starters_group_shared_risk(monkeypatch):
    response = make_app(monkeypatch, health_payload(last_verified="2026-09-12T12:00:00+00:00", age=60), weekly_score=12.0, unknown_players={"P0", "P1"}, authoritative_matchup=True).test_client().get("/team")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "MONITOR" in html
    assert "Team health verification required" in html
    assert "2 starter(s) are affected" in html
    assert html.count("Team health verification required") == 1


def test_no_urgent_risk_state_uses_calm_action(monkeypatch):
    response = make_app(monkeypatch, health_payload(last_verified="2026-09-12T12:00:00+00:00", age=60), weekly_score=12.0, authoritative_matchup=True, no_needs=True).test_client().get("/team")
    html = response.get_data(as_text=True)
    assert "Review lineup before lock" in html
    assert "No material supported risks identified." in html


AUTHORITATIVE_MATCHUP_FIELDS = {
    "matchup_population": "ALL_DEFENSES_BY_POSITION",
    "matchup_directionality": "LOWER_IS_HARDER",
    "matchup_source": "automated:nflverse",
    "matchup_source_authority": "automated",
    "matchup_sample_threshold_id": "matchup.sample.v1",
    "matchup_retrieved_at": "2999-01-01T00:00:00+00:00",
}


@pytest.mark.parametrize(
    "scenario,overrides,expect_rank_visible,expected_blocker",
    [
        ("authoritative", AUTHORITATIVE_MATCHUP_FIELDS, True, None),
        ("unverified_threshold", {**AUTHORITATIVE_MATCHUP_FIELDS, "matchup_sample_threshold_id": None}, False, "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED"),
        ("missing_population", {**AUTHORITATIVE_MATCHUP_FIELDS, "matchup_population": None}, False, "MATCHUP_POPULATION_UNVERIFIED"),
        ("missing_directionality", {**AUTHORITATIVE_MATCHUP_FIELDS, "matchup_directionality": None}, False, "MATCHUP_DIRECTIONALITY_UNVERIFIED"),
        ("stale", {**AUTHORITATIVE_MATCHUP_FIELDS, "matchup_retrieved_at": "2020-01-01T00:00:00+00:00"}, False, "MATCHUP_DATA_STALE"),
        ("csv_non_automated", {**AUTHORITATIVE_MATCHUP_FIELDS, "matchup_source": "csv:defense-fp-against-2025.csv", "matchup_source_authority": None}, False, "MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE"),
        ("missing_source_authority_on_display_formatted_source", {**AUTHORITATIVE_MATCHUP_FIELDS, "matchup_source": "nfl_schedule + automated:nflverse", "matchup_source_authority": None}, False, "MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE"),
        ("missing_identity", {**AUTHORITATIVE_MATCHUP_FIELDS, "source_player_id": None, "local_player_id": None}, False, "MATCHUP_PLAYER_IDENTITY_UNAVAILABLE"),
        ("missing_opponent", {**AUTHORITATIVE_MATCHUP_FIELDS, "opponent": None}, False, "MATCHUP_OPPONENT_IDENTITY_UNAVAILABLE"),
    ],
)
def test_active_team_route_matchup_authority_matrix(monkeypatch, scenario, overrides, expect_rank_visible, expected_blocker):
    response = make_app(
        monkeypatch, health_payload(last_verified="2026-09-12T12:00:00+00:00", age=60),
        weekly_score=12.0, matchup_overrides=overrides, no_needs=True,
    ).test_client().get("/team")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "<details open" not in html
    if expect_rank_visible:
        assert ">10<" in html
        assert "Rank 1 is hardest" in html
        assert "ALL_DEFENSES_BY_POSITION" in html
    else:
        assert ">10<" not in html
        assert "Unavailable" in html
        assert expected_blocker in html


def test_trades_route_renders_blocked_integrity_when_partner_is_unavailable(monkeypatch):
    response = make_app(monkeypatch, health_payload()).test_client().get("/trades?team=2")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Trade Center Integrity" in html
    assert "READY</small><h3>NO" in html
    assert "PARTNER_ROSTER_EMPTY" in html
    assert "MATCHUP_FRESHNESS_UNKNOWN" in html
    assert "<details class=\"trade-integrity\">" in html


def test_trades_route_publishes_packages_with_fresh_source_timestamps(monkeypatch):
    timestamp = "2999-01-01T00:00:00+00:00"
    def enrich_with_fresh_evidence(cur, roster, week, **kwargs):
        return [{**player, "weekly_baseline": 10.0, "weekly_score": 10.0, "opponent": "SF", "matchup_rank": 10, "matchup_modifier": 0.0, "is_bye": False, "evidence_gaps": [], "matchup_source": "Controlled matchup", "matchup_retrieved_at": timestamp, "projection_source": "Controlled projection", "projection_retrieved_at": timestamp} for player in roster]
    response = make_app(monkeypatch, health_payload(), trade_partner=True, trade_enrichment=enrich_with_fresh_evidence).test_client().get("/trades?team=2")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "READY</small><h3>YES" in html
    assert "Trade Recommendation" in html
    assert "Controlled matchup" in html
    assert "Controlled projection" in html


@pytest.mark.parametrize("scenario,expected", [("ready", "Review Partner"), ("ready_empty", "READY: No evidence-supported trade package qualifies."), ("degraded", "RISK IMPACT"), ("blocked", "BLOCKED: Trade recommendations are unavailable."), ("identity_ambiguity", "TRADE_IDENTITY_AMBIGUOUS")])
def test_trade_scenarios_render_through_testing_only_route(monkeypatch, scenario, expected):
    response = make_app(monkeypatch, health_payload(), trade_scenario=scenario).test_client().get(f"/trades?trade_scenario={scenario}")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert expected in html
    assert "<details class=\"trade-integrity\">" in html
    assert "<details class=\"trade-identity\">" in html
