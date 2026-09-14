from pathlib import Path

import pytest
from flask import Flask, render_template


def base_intelligence(**overrides):
    data = {
        "season": 2026, "week": 1, "games": [], "top_signals": [], "high_risk": [],
        "team_strength_ranking": [], "best_team_outlooks": [], "injury_impact_games": [],
        "weather_impact_games": [], "favorable_matchups": [], "tough_matchups": [], "insights": {},
        "blockers": [{"name": "Missing injury reports", "detail": "Not ingested.", "impact": "Detail always Unavailable."}],
        "freshness_state": "UNAVAILABLE", "evidence_state": "UNAVAILABLE", "last_verified": None,
        "scheduled_games": 16, "missing_predictions": 16,
    }
    data.update(overrides)
    return data


@pytest.fixture
def app():
    templates_dir = str(Path(__file__).resolve().parents[1] / "templates")
    app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]), template_folder=templates_dir)
    app.config.update(TESTING=True, SECRET_KEY="test")
    app.jinja_env.globals["url_for"] = lambda *a, **k: "/"
    app.jinja_env.globals["csrf_token"] = lambda: "test-csrf"
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def render(app, client, **overrides):
    @app.get("/nfl-intelligence-test")
    def _route():
        return render_template("nfl_intelligence.html", season=2026, week=1, intelligence=base_intelligence(**overrides), available_weeks=[1, 2])
    return client.get("/nfl-intelligence-test")


def test_page_loads(app, client):
    assert render(app, client).status_code == 200


def test_no_wagering_terms_rendered(app, client):
    html = render(app, client).get_data(as_text=True).upper()
    # The header intentionally disclaims wagering ("no wagering guidance is produced here");
    # that disclaimer sentence is the only permitted appearance of "WAGER".
    assert html.count("WAGER") == 2
    assert "NO WAGERING GUIDANCE IS PRODUCED HERE" in html
    for banned in ("BANKROLL", "STAKE", "KELLY", "PARLAY", "ODDS SHOPPING", "CLV", "MAX PLAY", "HIGH UNIT"):
        assert banned not in html


def test_unavailable_state_renders(app, client):
    html = render(app, client).get_data(as_text=True)
    assert "No games are scheduled for this week." in html
    assert "No scheduled games for this week" in html
    assert 'name="week"' in html
    assert 'value="2"' in html
    assert 'id="nfli-refresh-btn"' in html
    assert "/api/market-intelligence/refresh" in html


def test_game_list_renders_with_confidence_separate_from_prediction(app, client):
    games = [{"game_id": "g1", "away_team": "A", "home_team": "H", "win_team": "H", "opponent": "A",
              "has_prediction": True, "reason": None,
              "win_probability": 0.8, "confidence_available": True, "confidence": 0.6, "disagreement": 0.4,
              "signal": "MODERATE SIGNAL", "grade": "SOLID", "action": "WATCH CLOSELY", "risk": None, "freshness": "FRESH", "market_home_probability": 0.8,
              "team_strength_supported": False, "away_elo": None, "home_elo": None,
              "injury_supported": False, "away_injury": None, "home_injury": None, "injury_total": None,
              "injury_impact": "UNAVAILABLE", "weather_supported": False, "weather": None, "weather_flag": None}]
    html = render(app, client, games=games).get_data(as_text=True)
    assert "A @ H" in html
    assert "SOLID" in html
    assert "WATCH CLOSELY" in html


def test_game_without_prediction_shows_note_not_hidden(app, client):
    games = [{"game_id": "g1", "away_team": "A", "home_team": "H", "win_team": None, "opponent": None,
              "has_prediction": False, "reason": "No market-derived prediction has been ingested for this game yet.",
              "win_probability": None, "confidence_available": False, "confidence": None, "disagreement": None,
              "signal": "INSUFFICIENT EVIDENCE", "grade": "INSUFFICIENT EVIDENCE", "action": "INSUFFICIENT EVIDENCE", "risk": "No supported prediction exists for this game.", "freshness": "UNAVAILABLE",
              "market_home_probability": None, "team_strength_supported": False, "away_elo": None, "home_elo": None,
              "injury_supported": False, "away_injury": None, "home_injury": None, "injury_total": None,
              "injury_impact": "UNAVAILABLE", "weather_supported": False, "weather": None, "weather_flag": None}]
    html = render(app, client, games=games).get_data(as_text=True)
    assert "A @ H" in html
    assert "INSUFFICIENT EVIDENCE" in html
    assert "No market-derived prediction has been ingested" in html


def test_blocker_states_render(app, client):
    html = render(app, client).get_data(as_text=True)
    assert "Missing injury reports" in html
    assert "Recommendation impact" in html


def test_diagnostics_collapsed_by_default(app, client):
    html = render(app, client).get_data(as_text=True)
    assert '<details class="nfli-details"><summary>Diagnostics</summary>' in html


def test_full_schedule_renders_even_without_predictions(app, client):
    games = []
    for i in range(16):
        games.append({"game_id": f"g{i}", "away_team": f"A{i}", "home_team": f"H{i}", "win_team": None, "opponent": None,
                      "has_prediction": False, "reason": "No market-derived prediction has been ingested for this game yet.",
                      "win_probability": None, "confidence_available": False, "confidence": None, "disagreement": None,
                          "signal": "INSUFFICIENT EVIDENCE", "grade": "INSUFFICIENT EVIDENCE", "action": "INSUFFICIENT EVIDENCE", "risk": "No supported prediction exists for this game.", "freshness": "UNAVAILABLE",
                      "market_home_probability": None, "team_strength_supported": False, "away_elo": None, "home_elo": None,
                      "injury_supported": False, "away_injury": None, "home_injury": None, "injury_total": None,
                          "injury_impact": "UNAVAILABLE", "weather_supported": False, "weather": None, "weather_flag": None})
    html = render(app, client, games=games, scheduled_games=16, missing_predictions=16).get_data(as_text=True)
    assert html.count("INSUFFICIENT EVIDENCE") >= 16
    for i in range(16):
        assert f"A{i} @ H{i}" in html


def test_top5_team_strength_section_renders_when_supported(app, client):
    games = [{"game_id": "g1", "away_team": "A", "home_team": "H", "win_team": "H", "opponent": "A",
              "has_prediction": True, "reason": None, "win_probability": 0.8, "confidence_available": True,
              "confidence": 0.9, "signal": "STRONG SIGNAL", "grade": "ELITE", "action": "STRONG SIGNAL",
              "risk": None, "freshness": "FRESH", "injury_impact": "LOW", "weather_flag": "LOW",
              "team_strength_supported": True, "away_elo": 1450, "home_elo": 1600, "elo_diff": 150,
              "injury_total": -1, "weather_supported": True, "weather": {"wind_speed_10m": 5, "precipitation": 0}}]
    picks = [{**games[0], "top_pick_reason": "Highest confidence available"}]
    html = render(app, client, games=games, top_signals=picks).get_data(as_text=True)
    assert "Top Picks This Week" in html and "All Games" in html
    assert "Top 5 Games to Watch" not in html
    assert "Top 5 Team Strength (Elo)" not in html
    assert "1600" in html and "Elo:" in html
    assert "View Details" in html


def test_removed_duplicate_sections_do_not_render(app, client):
    html = render(app, client).get_data(as_text=True)
    for heading in ("Top 5 Team Strength", "Best Team Outlooks", "Top 5 Most Favorable Matchups", "Top 5 Tough Matchups"):
        assert heading not in html


def test_top_signals_never_empty_when_games_exist_without_predictions(app, client):
    top_signals = [{"game_id": "g1", "away_team": "A", "home_team": "H", "win_team": None, "opponent": None,
                    "has_prediction": False, "reason": "No market-derived prediction has been ingested for this game yet.",
                    "win_probability": None, "confidence_available": False, "confidence": None,
                    "signal": "INSUFFICIENT EVIDENCE", "confidence_label": "INSUFFICIENT EVIDENCE",
                    "risk": "No supported prediction exists for this game.", "freshness": "UNAVAILABLE"}]
    html = render(app, client, top_signals=top_signals).get_data(as_text=True)
    assert "Top Picks This Week" in html
    assert "A @ H" in html


def test_stale_state_renders(app, client):
    games = [{"game_id": "g1", "away_team": "A", "home_team": "H", "win_team": "H", "opponent": "A",
              "has_prediction": True, "reason": None,
              "win_probability": 0.8, "confidence_available": True, "confidence": 0.9, "disagreement": 0.1,
              "signal": "INSUFFICIENT EVIDENCE", "grade": "INSUFFICIENT EVIDENCE", "action": "INSUFFICIENT EVIDENCE", "risk": "Evidence is stale.", "freshness": "STALE",
              "market_home_probability": 0.8, "team_strength_supported": False, "away_elo": None, "home_elo": None,
              "injury_supported": False, "away_injury": None, "home_injury": None, "injury_total": None,
              "injury_impact": "UNAVAILABLE", "weather_supported": False, "weather": None, "weather_flag": None}]
    html = render(app, client, games=games, freshness_state="STALE", evidence_state="BLOCKED").get_data(as_text=True)
    assert "STALE" in html
    assert "INSUFFICIENT EVIDENCE" in html
