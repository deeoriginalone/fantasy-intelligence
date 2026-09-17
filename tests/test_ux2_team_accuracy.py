from services.lineup_evidence import build_matchup_evidence
from services.ux2_team_accuracy import build_team_accuracy_contract

POSITIONS = ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")
NOW = "2026-09-12T12:00:00+00:00"


def settings(full_ppr=True): return {"state":"AVAILABLE","source":"Sleeper API","blocker":None,"starter_slots":{"QB":1,"RB":2,"WR":2,"TE":1,"FLEX":1,"K":1,"DEF":1},"flex_eligible_positions":["RB","WR","TE"],"full_ppr":full_ppr}
def needs(): return {key:{"state":"AVAILABLE","required_slots":1,"rostered":1,"shortage":0,"need":"COVERED","blocker":None} for key in POSITIONS}
def health(): return {"state":"AVAILABLE","source":"Sleeper","freshness_state":"FRESH","blocker":None}


def starter(**changes):
    """A starter row carrying a real services.lineup_evidence.build_matchup_evidence result.

    Matchup authority is derived here exactly the way production enrichment
    derives it, so tests exercise the same shared contract the app consumes.
    """
    row = {
        "player": "A", "position": "WR", "opponent": "SF",
        "matchup_rank": 12, "matchup_modifier": 0.05,
        "evidence_gaps": [], "is_bye": False,
        "source_player_id": "sleeper-1", "local_player_id": 1,
        "matchup_source": "automated:nflverse", "matchup_source_authority": "automated",
        "matchup_retrieved_at": NOW,
        "matchup_sample_threshold_id": "matchup.sample.v1",
        "matchup_population": "ALL_DEFENSES_BY_POSITION",
        "matchup_directionality": "LOWER_IS_HARDER",
    }
    row.update(changes)
    row["lineup_evidence"] = {"matchup": build_matchup_evidence(row, season=2026, week=3, now=NOW)}
    return row


def test_complete_evidence_is_trusted():
    result=build_team_accuracy_contract([], [starter(opponent_name="San Francisco 49ers")], settings(), needs(), health())
    assert result["trusted"] is True
    assert result["scoring"]["format"] == "Full PPR"
    assert set(result["team_needs"]["positions"]) == set(POSITIONS)
    assert result["matchups"]["rows"][0]["opponent_name"] == "San Francisco 49ers"
    assert result["matchups"]["rows"][0]["matchup_rank"] == 12

def test_non_full_ppr_blocks_full_ppr_claim():
    result=build_team_accuracy_contract([], [starter()], settings(False), needs(), health())
    assert result["trusted"] is False
    assert "FULL_PPR_SCORING_NOT_VERIFIED" in result["blockers"]

def test_missing_matchup_is_unavailable_not_neutral():
    result=build_team_accuracy_contract([], [starter(opponent=None,matchup_rank=None,matchup_modifier=None)], settings(), needs(), health())
    assert result["matchups"]["rows"][0]["state"] == "UNAVAILABLE"
    assert "MATCHUP_RANK_MISSING" in result["matchups"]["rows"][0]["blockers"]
    assert result["matchups"]["rows"][0]["matchup_rank"] is None

def test_blocked_health_reduces_trust():
    blocked={"state":"BLOCKED","source":"Sleeper","freshness_state":"BLOCKED","blocker":"HEALTH_REFRESH_FAILED"}
    result=build_team_accuracy_contract([], [starter()], settings(), needs(), blocked)
    assert result["trusted"] is False
    assert "HEALTH_REFRESH_FAILED" in result["blockers"]


def test_unverified_sample_threshold_suppresses_rank():
    result = build_team_accuracy_contract([], [starter(matchup_sample_threshold_id=None)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in row["blockers"]


def test_missing_population_suppresses_rank():
    result = build_team_accuracy_contract([], [starter(matchup_population=None)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_POPULATION_UNVERIFIED" in row["blockers"]


def test_missing_directionality_suppresses_rank():
    result = build_team_accuracy_contract([], [starter(matchup_directionality=None)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_DIRECTIONALITY_UNVERIFIED" in row["blockers"]


def test_stale_evidence_suppresses_rank():
    result = build_team_accuracy_contract([], [starter(matchup_retrieved_at="2020-01-01T00:00:00+00:00")], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_DATA_STALE" in row["blockers"]


def test_csv_non_automated_evidence_suppresses_rank():
    result = build_team_accuracy_contract([], [starter(matchup_source="csv:defense-fp-against-2025.csv", matchup_source_authority=None)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE" in row["blockers"]


def test_missing_structured_source_authority_fails_closed_on_display_formatted_source():
    result = build_team_accuracy_contract([], [starter(matchup_source="nfl_schedule + automated:nflverse:weekly-w3", matchup_source_authority=None)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE" in row["blockers"]


def test_unresolved_identity_suppresses_rank():
    result = build_team_accuracy_contract([], [starter(source_player_id=None, local_player_id=None)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_PLAYER_IDENTITY_UNAVAILABLE" in row["blockers"]


def test_missing_opponent_suppresses_rank_via_shared_contract():
    result = build_team_accuracy_contract([], [starter(opponent=None)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] is None
    assert "MATCHUP_OPPONENT_IDENTITY_UNAVAILABLE" in row["blockers"]


def test_population_and_plain_language_directionality_appear_for_authoritative_evidence():
    result = build_team_accuracy_contract([], [starter()], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["comparison_population"] == "ALL_DEFENSES_BY_POSITION"
    assert row["matchup_context"] == "Rank 1 is hardest; the highest rank is easiest within ALL_DEFENSES_BY_POSITION."


def test_directionality_uses_supplied_population_size_without_inventing_one():
    with_size = starter()
    with_size["matchup_publication_lineage"] = {"publication_contracts": {"population": {"size": 32}}}
    with_size["lineup_evidence"] = {"matchup": build_matchup_evidence(with_size, season=2026, week=3, now=NOW)}
    result = build_team_accuracy_contract([], [with_size], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_context"] == "Rank 1 is hardest; rank 32 is easiest within ALL_DEFENSES_BY_POSITION."


def test_zero_matchup_rank_is_distinct_from_unavailable():
    result = build_team_accuracy_contract([], [starter(matchup_rank=0)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] == 0
    assert row["matchup_rank"] is not None


def test_unfavorable_rank_is_distinct_from_unavailable():
    result = build_team_accuracy_contract([], [starter(matchup_rank=32)], settings(), needs(), health())
    row = result["matchups"]["rows"][0]
    assert row["matchup_rank"] == 32
