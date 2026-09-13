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


def test_lineup_route_delegates_to_explainable_payload():
    source = Path("owner_operations.py").read_text(encoding="utf-8")
    start = source.index('@bp.route("/lineup")')
    end = source.index('@bp.route("/waivers")', start)
    segment = source[start:end]

    assert "context, roster, meta = current_roster(cur)" in segment
    assert "lineup_intelligence = build_lineup_intelligence(roster)" in segment
    assert "context=context" in segment
    assert "meta=meta" in segment
    assert "lineup_intelligence=lineup_intelligence" in segment


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
