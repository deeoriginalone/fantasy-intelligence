import os

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_NAME", "fantasy_intelligence")
os.environ.setdefault("DB_USER", "fantasy")
os.environ.setdefault("DB_PASSWORD", "fantasy")
os.environ.setdefault("SLEEPER_LEAGUE_ID", "league-123")
os.environ.setdefault("SLEEPER_DRAFT_ID", "draft-123")

import pytest
from yahoo_pickem import PickemGame, build_week
from app import app


def test_admin_routes_require_auth():
    client = app.test_client()
    resp = client.post("/sleeper-sync")
    assert resp.status_code == 401

    resp = client.post("/draft-sync")
    assert resp.status_code == 401


def test_valid_session_csrf_allows_admin_form_submit():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["csrf_token"] = "session-token"
        sess["user_role"] = "admin"

    resp = client.post(
        "/draftboard/strategy",
        data={"strategy": "ZERO_RB", "csrf_token": "session-token"},
        follow_redirects=False,
    )
    assert resp.status_code in {200, 302}


def test_invalid_csrf_is_rejected_for_form_posts():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["csrf_token"] = "valid-token"

    resp = client.post(
        "/draftboard/strategy",
        data={"strategy": "ZERO_RB", "csrf_token": "wrong-token"},
        follow_redirects=False,
    )
    assert resp.status_code in {401, 403}


def test_duplicate_games_are_rejected():
    game = PickemGame(
        game_id="g1",
        season=2026,
        week=1,
        kickoff="2026-09-10T17:20:00-07:00",
        away_team="DAL",
        home_team="PHI",
        yahoo_away_pct=0.35,
        yahoo_home_pct=0.65,
        market_home_probability=0.64,
    )

    with pytest.raises(ValueError):
        build_week([game, game])


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError):
        PickemGame(
            game_id="g2",
            season=2026,
            week=1,
            kickoff="2026-09-10T17:20:00-07:00",
            away_team="BUF",
            home_team="NYJ",
            yahoo_away_pct=0.60,
            yahoo_home_pct=0.60,
            market_home_probability=0.50,
        ).validate()


def test_percentages_must_total_approximately_100_percent():
    with pytest.raises(ValueError):
        PickemGame(
            game_id="g3",
            season=2026,
            week=1,
            kickoff="2026-09-10T17:20:00-07:00",
            away_team="KC",
            home_team="LAC",
            yahoo_away_pct=0.40,
            yahoo_home_pct=0.40,
            market_home_probability=0.52,
        ).validate()
