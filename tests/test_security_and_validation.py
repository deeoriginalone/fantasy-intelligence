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


def test_survivor_reset_requires_csrf():
    client = app.test_client()
    resp = client.post("/survivor/reset", data={"season": 2026, "week": 1, "pool": "default", "team": "JAX"})
    assert resp.status_code == 403


def test_survivor_select_requires_csrf():
    client = app.test_client()
    resp = client.post(
        "/survivor/select",
        data={"season": 2026, "week": 1, "pool": "default", "team": "JAX", "probability": 0.7, "score": 0.7},
    )
    assert resp.status_code == 403


def test_survivor_status_requires_csrf():
    client = app.test_client()
    resp = client.post(
        "/survivor/status",
        data={"season": 2026, "week": 1, "pool": "default", "team": "JAX", "status": "won"},
    )
    assert resp.status_code == 403


def test_survivor_manual_pick_accepts_any_eligible_team_without_probability():
    from survivor_store import connect, ensure_pool, week_selection

    pool_key = "ux8-manual-pick-route-test"
    ensure_pool(pool_key, "Manual Pick Route Test", 2026)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["csrf_token"] = "session-token"
    try:
        resp = client.post(
            "/survivor/select",
            data={"season": 2026, "week": 1, "pool": pool_key, "team": "jax", "csrf_token": "session-token"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        row = week_selection(pool_key, 2026, 1)
        assert row["team"] == "JAX"
        assert row["model_probability"] is None
    finally:
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM survivor_selections WHERE pool_key=%s", (pool_key,))
                cur.execute("DELETE FROM survivor_pools WHERE pool_key=%s", (pool_key,))
            conn.commit()
        finally:
            conn.close()


def test_survivor_manual_pick_rejects_unknown_team():
    from survivor_store import connect, ensure_pool, week_selection

    pool_key = "ux8-manual-pick-invalid-test"
    ensure_pool(pool_key, "Manual Pick Invalid Test", 2026)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["csrf_token"] = "session-token"
    try:
        resp = client.post(
            "/survivor/select",
            data={"season": 2026, "week": 1, "pool": pool_key, "team": "ZZZ", "csrf_token": "session-token"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert week_selection(pool_key, 2026, 1) is None
    finally:
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM survivor_selections WHERE pool_key=%s", (pool_key,))
                cur.execute("DELETE FROM survivor_pools WHERE pool_key=%s", (pool_key,))
            conn.commit()
        finally:
            conn.close()


def test_market_refresh_endpoint_requires_auth():
    client = app.test_client()
    resp = client.post("/api/market-intelligence/refresh", json={"season": 2026, "week": 1, "dry_run": True})
    assert resp.status_code == 401


def test_market_refresh_endpoint_accepts_valid_session_csrf(monkeypatch):
    import market_routes

    monkeypatch.setattr(market_routes, "run", lambda season, week, strategy, dry_run: {"status": "dry-run", "season": season, "week": week})

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["csrf_token"] = "session-token"

    resp = client.post(
        "/api/market-intelligence/refresh",
        json={"season": 2026, "week": 1, "dry_run": True},
        headers={"X-CSRF-Token": "session-token"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "dry-run"


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
