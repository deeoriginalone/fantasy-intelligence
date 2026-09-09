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
