from pathlib import Path

from services.weekly_lineup_intelligence import build_lineup_intelligence


def player(name, position, score=10.0):
    return {
        "player": name,
        "position": position,
        "weekly_score": score,
        "weekly_baseline": score,
        "projection": score * 17,
        "rank": 100,
        "injury_status": "Healthy",
        "injury_multiplier": 1.0,
        "is_bye": False,
        "opponent": "X",
        "matchup_rank": 16,
        "matchup_modifier": 0.0,
    }


def test_lineup_route_redirects_to_unified_team_page():
    source = Path("owner_operations.py").read_text(encoding="utf-8")
    start = source.index('@bp.route("/lineup")')
    end = source.index('@bp.route("/waivers")', start)
    segment = source[start:end]

    assert 'redirect(url_for("owner_ops.team_page") + "#lineup", code=302)' in segment


def test_team_route_delegates_to_explainable_payload():
    source = Path("owner_operations.py").read_text(encoding="utf-8")
    start = source.index('@bp.route("/team")')
    end = source.index('@bp.route("/lineup")', start)
    segment = source[start:end]

    assert "context, roster, meta = current_roster(cur)" in segment
    assert "lineup_intelligence = build_lineup_intelligence(roster)" in segment
    assert "lineup_intelligence=lineup_intelligence" in segment


def test_lineup_route_returns_302_and_preserves_fragment():
    import os

    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "5433")
    os.environ.setdefault("DB_NAME", "fantasy_intelligence")
    os.environ.setdefault("DB_USER", "fantasy")
    os.environ.setdefault("DB_PASSWORD", "fantasy")
    os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
    os.environ.setdefault("SLEEPER_LEAGUE_ID", "league-123")
    os.environ.setdefault("SLEEPER_DRAFT_ID", "draft-123")
    from app import app

    response = app.test_client().get("/lineup", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/team#lineup")


def test_lineup_payload_uses_explicit_decisions_and_bench_order():
    roster = [
        player("QB1", "QB", 20),
        player("RB1", "RB", 18),
        player("RB2", "RB", 17),
        player("WR1", "WR", 16),
        player("WR2", "WR", 15),
        player("TE1", "TE", 12),
        player("FLEX1", "WR", 11),
        player("K1", "K", 9),
        player("DEF1", "DEF", 8),
        player("BENCH1", "WR", 7),
    ]
    payload = build_lineup_intelligence(roster)

    assert all("decision" in item for item in payload["start_sit_decisions"])
    assert not any(item.get("action") == "HOLD" for item in payload["start_sit_decisions"])
    assert {item["decision"] for item in payload["start_sit_decisions"]} <= {"START", "FLEX", "MONITOR"}
    assert [item["bench_order"] for item in payload["bench"]] == [1]
    assert payload["metric_definitions"]["baseline"]
    assert payload["metric_definitions"]["weekly_score"]
