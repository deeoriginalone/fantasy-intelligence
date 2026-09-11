from services.matchup_intelligence import build_matchup_intelligence
from services.weekly_lineup_intelligence import build_lineup_intelligence


def player(name="A", position="QB", **updates):
    row = {
        "player": name,
        "position": position,
        "rank": 100,
        "projection": 170,
        "weekly_baseline": 10,
        "weekly_score": 10,
        "opponent": "X",
        "matchup_rank": 15,
        "matchup_modifier": 0.0,
        "fp_allowed": 20,
        "injury_status": "Healthy",
        "injury_multiplier": 1.0,
        "is_bye": False,
        "evidence_gaps": [],
    }
    row.update(updates)
    return row


def roster():
    return [
        player("QB1", "QB"), player("RB1", "RB"),
        player("RB2", "RB"), player("WR1", "WR"),
        player("WR2", "WR"), player("TE1", "TE"),
        player("FLEX", "WR"), player("K1", "K"),
        player("DEF1", "DEF"),
    ]


def test_matchup_contract_includes_shared_integrity():
    rows = roster()
    result = build_matchup_intelligence(rows)
    assert result["integrity"]["player_count"] == len(rows)
    assert result["integrity"]["completeness_score"] == 100


def test_lineup_contract_includes_shared_integrity():
    rows = roster()
    result = build_lineup_intelligence(rows)
    assert result["integrity"]["player_count"] == len(rows)
    assert result["integrity"]["unknown_health_players"] == 0


def test_missing_health_and_matchup_are_visible_in_both_contracts():
    rows = roster()
    rows[0].update({
        "injury_status": "Unknown",
        "matchup_rank": None,
        "evidence_gaps": [
            "INJURY_STATUS_UNRESOLVED",
            "MATCHUP_RANK_UNAVAILABLE",
        ],
    })
    for result in (
        build_matchup_intelligence(rows),
        build_lineup_intelligence(rows),
    ):
        assert result["integrity"]["unknown_health_players"] == 1
        assert result["integrity"]["missing_matchups"] == 1
        assert "INJURY_STATUS_UNRESOLVED" in result["integrity"]["blockers"]

def test_freshness_metadata_flows_through_both_contracts():
    rows = roster()
    metadata = {
        "roster_updated_at": "2999-01-01T00:00:00+00:00",
        "injury_updated_at": "2999-01-01T00:00:00+00:00",
        "matchup_updated_at": "2999-01-01T00:00:00+00:00",
        "projection_updated_at": "2999-01-01T00:00:00+00:00",
    }
    for result in (
        build_matchup_intelligence(rows, freshness_metadata=metadata),
        build_lineup_intelligence(rows, freshness_metadata=metadata),
    ):
        freshness = result["integrity"]["freshness"]
        assert freshness["domains"]["roster"]["source_field"] == "roster_updated_at"
        assert freshness["domains"]["injury"]["source_field"] == "injury_updated_at"
        assert freshness["domains"]["matchup"]["source_field"] == "matchup_updated_at"
        assert freshness["domains"]["projection"]["source_field"] == "projection_updated_at"
        assert all(item["status"] == "FRESH" for item in freshness["domains"].values())
        assert freshness["blockers"] == []


def test_missing_freshness_metadata_remains_unknown_in_both_contracts():
    rows = roster()
    for result in (
        build_matchup_intelligence(rows),
        build_lineup_intelligence(rows),
    ):
        freshness = result["integrity"]["freshness"]
        assert freshness["has_unknown"] is True
        assert {item["status"] for item in freshness["domains"].values()} == {"UNKNOWN"}
        assert {
            "ROSTER_FRESHNESS_UNKNOWN",
            "INJURY_FRESHNESS_UNKNOWN",
            "MATCHUP_FRESHNESS_UNKNOWN",
            "PROJECTION_FRESHNESS_UNKNOWN",
        } <= set(result["integrity"]["blockers"])
