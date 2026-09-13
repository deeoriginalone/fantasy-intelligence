from services.team_health import team_health_contract
from services.ux2_team_accuracy import build_team_accuracy_contract
from services.ux_evidence import roster_lineage


def settings():
    return {"state": "AVAILABLE", "source": "Sleeper API", "full_ppr": True, "starter_slots": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DEF": 1}, "flex_eligible_positions": ["RB", "WR", "TE"]}


def needs():
    return {position: {"state": "AVAILABLE"} for position in ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")}


def test_k_and_defense_matchup_are_not_applicable():
    starters = [
        {"player": "Kicker", "position": "K", "opponent": "KC", "matchup_rank": None, "matchup_modifier": 0.0, "is_bye": False},
        {"player": "Baltimore Ravens", "position": "DEF", "opponent": "IND", "matchup_rank": None, "matchup_modifier": 0.0, "is_bye": False},
    ]
    result = build_team_accuracy_contract([], starters, settings(), needs(), {"state": "AVAILABLE"})
    assert all(row["state"] == "NOT_APPLICABLE" for row in result["matchups"]["rows"])
    assert "MATCHUP_RANK_MISSING" not in result["blockers"]


def test_team_health_excludes_team_defense_from_player_counts():
    result = team_health_contract([
        {"position": "QB", "injury_status": "ACTIVE"},
        {"position": "DEF", "injury_status": "Unknown"},
    ])
    assert result["healthy"] == 1
    assert result["unknown"] == 0


def test_rostered_owner_lineage_is_explicit():
    row = roster_lineage([{"player": "Player", "position": "WR", "ownership": "ROSTERED", "ownership_source": "Sleeper API"}])[0]
    assert row["ownership"]["state"] == "AVAILABLE"
    assert row["ownership"]["value"] == "ROSTERED"
    assert row["ownership"]["source"] == "Sleeper API"
