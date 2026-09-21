from pathlib import Path

from services.weekly_lineup_intelligence import build_lineup_intelligence
from owner_operations import build_lineup_reconciliation, build_recommended_bench


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
    assert "lineup_intelligence = build_lineup_intelligence(roster, current_starters=current_sleeper_starters)" in segment
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


def test_lineup_reconciliation_keeps_sleeper_truth_separate_from_recommendation():
    current = [{"player": "Justin Herbert", "position": "QB", "sleeper_current_starter": True, "sleeper_lineup_slot": "QB", "injury_status": "Healthy"}]
    recommended = [{"player": "Joe Burrow", "position": "QB", "slot": "QB", "vacant": False}]
    result = build_lineup_reconciliation(current, recommended)
    assert result["state"] == "AVAILABLE"
    assert result["current"][0]["player"] == "Justin Herbert"
    assert result["changes"][0]["slot"] == "QB"
    assert result["changes"][0]["current"] == "Justin Herbert"
    assert result["changes"][0]["recommended"] == "Joe Burrow"
    assert result["changes"][0]["current_id"] == "Justin Herbert"
    assert result["changes"][0]["recommended_id"] == "Joe Burrow"


def test_lineup_reconciliation_numbers_duplicate_sleeper_running_back_slots():
    current = [
        {"player": "Rico Dowdle", "position": "RB", "sleeper_current_starter": True, "sleeper_lineup_slot": "RB", "sleeper_lineup_index": 2},
        {"player": "RB One", "position": "RB", "sleeper_current_starter": True, "sleeper_lineup_slot": "RB", "sleeper_lineup_index": 1},
    ]
    recommended = [
        {"player": "RB One", "position": "RB", "slot": "RB1", "vacant": False},
        {"player": "Kenny Gainwell", "position": "RB", "slot": "RB2", "vacant": False},
    ]
    result = build_lineup_reconciliation(current, recommended)
    assert result["changes"][0]["slot"] == "RB2"
    assert result["changes"][0]["current"] == "Rico Dowdle"
    assert result["changes"][0]["recommended"] == "Kenny Gainwell"
    assert result["changes"][0]["current_id"] == "Rico Dowdle"
    assert result["changes"][0]["recommended_id"] == "Kenny Gainwell"


def test_lineup_reconciliation_fails_closed_without_sleeper_starters():
    result = build_lineup_reconciliation([{"player": "Joe Burrow"}], [{"player": "Joe Burrow", "slot": "QB", "vacant": False}])
    assert result["state"] == "UNAVAILABLE"


def test_reconciliation_uses_stable_ids_and_changed_slots_only():
    roster = [
        {"player": "Current QB", "source_player_id": "qb-old", "sleeper_current_starter": True, "sleeper_lineup_slot": "QB", "injury_status": "Healthy"},
        {"player": "Incoming QB", "source_player_id": "qb-new", "sleeper_current_starter": False, "sleeper_lineup_slot": None, "injury_status": "Healthy"},
        {"player": "Unchanged RB", "source_player_id": "rb-1", "sleeper_current_starter": True, "sleeper_lineup_slot": "RB", "sleeper_lineup_index": 1, "injury_status": "Healthy"},
    ]
    result = build_lineup_reconciliation(roster, [
        {"player": "Incoming QB", "source_player_id": "qb-new", "position": "QB", "slot": "QB", "vacant": False},
        {"player": "Unchanged RB", "source_player_id": "rb-1", "position": "RB", "slot": "RB1", "vacant": False},
    ])
    assert [(item["current_id"], item["recommended_id"], item["slot"]) for item in result["changes"]] == [("qb-old", "qb-new", "QB")]
    assert [item["player"] for item in result["changed_recommended"]] == ["Incoming QB"]


def test_recommended_bench_is_roster_minus_recommended_starter_ids():
    roster = [
        {"player": "Starter", "source_player_id": "p1", "position": "WR", "weekly_score": 10, "weekly_baseline": 10, "injury_status": "Healthy", "injury_multiplier": 1, "is_bye": False},
        {"player": "Healthy Bench", "source_player_id": "p2", "position": "WR", "weekly_score": 8, "weekly_baseline": 8, "injury_status": "Healthy", "injury_multiplier": 1, "is_bye": False},
        {"player": "Out Bench", "source_player_id": "p3", "position": "RB", "weekly_score": 7, "weekly_baseline": 7, "injury_status": "Out", "injury_multiplier": 0, "is_bye": False},
    ]
    bench = build_recommended_bench(roster, [{"player": "Starter", "source_player_id": "p1", "vacant": False}])
    assert [item["source_player_id"] for item in bench] == ["p2", "p3"]
    assert all(item["source_player_id"] != "p1" for item in bench)
    assert bench[0]["decision"] == "SIT"
    assert bench[1]["decision"] == "MONITOR"
