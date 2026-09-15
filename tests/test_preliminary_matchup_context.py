from services.preliminary_matchup_context import build_preliminary_matchup_context
from pathlib import Path

from services.weekly_lineup_intelligence import optimize_lineup


def evidence(**updates):
    value = {
        "season": 2026,
        "status": "BLOCKED",
        "blocker": "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED",
        "scoring_context": "FULL_PPR",
        "rows": [{"position": "WR", "defense_team": "KC", "fp_per_game_allowed": 18.25, "completed_games": 1}],
        "freshness": {"status": "FRESH", "blocker": None},
        "completeness": {"complete": True, "defense_count": 32, "required_defenses": 32},
        "provenance": {"source": "https://official.example/stats_player_week_2026.csv.gz", "retrieved_at": "2026-09-15T12:00:00+00:00"},
    }
    value.update(updates)
    return value


def test_complete_fresh_evidence_is_informational_without_rank_or_modifier():
    result = build_preliminary_matchup_context(evidence())
    matchup = result["matchups"][0]
    assert result["state"] == "PRELIMINARY"
    assert result["authority"] == "INFORMATIONAL_ONLY"
    assert matchup["completed_games"] == 1
    assert matchup["defenses_represented"] == 32
    assert matchup["scoring_context"] == "FULL_PPR"
    assert matchup["unit"] == "fantasy_points_per_completed_game"
    assert "matchup_rank" not in matchup
    assert "matchup_modifier" not in matchup
    assert result["decision_effect"] == "NONE"


def test_missing_provenance_is_unavailable():
    result = build_preliminary_matchup_context(evidence(provenance={"source": "official"}))
    assert result["state"] == "UNAVAILABLE"
    assert result["blocker"] == "MATCHUP_PROVENANCE_UNAVAILABLE"


def test_stale_evidence_is_stale():
    result = build_preliminary_matchup_context(evidence(freshness={"status": "STALE", "blocker": "MATCHUP_DATA_STALE"}))
    assert result["state"] == "STALE"
    assert result["blocker"] == "MATCHUP_DATA_STALE"


def test_incomplete_and_invalid_evidence_are_blocked():
    incomplete = build_preliminary_matchup_context(evidence(completeness={"complete": False, "defense_count": 30, "required_defenses": 32}))
    invalid = build_preliminary_matchup_context(evidence(scoring_context="HALF_PPR"))
    assert incomplete["state"] == "BLOCKED"
    assert incomplete["blocker"] == "CURRENT_SEASON_DEFENSE_COMPLETENESS_REQUIRED"
    assert invalid["state"] == "BLOCKED"
    assert invalid["blocker"] == "UNSUPPORTED_SCORING"


def test_historical_source_cannot_be_current_context():
    result = build_preliminary_matchup_context(evidence(provenance={"source": "csv:defense-fp-against-2025.csv", "retrieved_at": "2026-09-15T12:00:00+00:00"}))
    assert result["state"] == "BLOCKED"
    assert result["blocker"] == "HISTORICAL_MATCHUP_NOT_CURRENT"


def test_roster_projection_selects_only_matching_position_and_opponent():
    result = build_preliminary_matchup_context(evidence(rows=[
        {"position": "WR", "defense_team": "KC", "fp_per_game_allowed": 18.25, "completed_games": 1},
        {"position": "RB", "defense_team": "DEN", "fp_per_game_allowed": 21.0, "completed_games": 1},
    ]), roster=[{"position": "WR", "opponent": "KC"}])
    assert [(item["position"], item["defense_team"]) for item in result["matchups"]] == [("WR", "KC")]


def test_preliminary_context_does_not_change_lineup_decisions():
    roster = [
        {"player": "QB", "position": "QB", "slot": "QB", "weekly_score": 10, "weekly_baseline": 10, "projection": 170, "rank": 1, "injury_status": "Healthy", "injury_multiplier": 1, "is_bye": False, "opponent": "KC", "matchup_rank": None, "matchup_modifier": 0},
        {"player": "K", "position": "K", "slot": "K", "weekly_score": 5, "weekly_baseline": 5, "projection": 85, "rank": 1, "injury_status": "Healthy", "injury_multiplier": 1, "is_bye": False, "opponent": "KC", "matchup_rank": None, "matchup_modifier": 0},
    ]
    before = optimize_lineup([dict(player) for player in roster])
    build_preliminary_matchup_context(evidence(), roster=roster)
    after = optimize_lineup([dict(player) for player in roster])
    assert before == after


def test_manager_facing_wording_contains_only_informational_context():
    template = Path("templates/_preliminary_matchup_context.html").read_text(encoding="utf-8")
    for phrase in ("PRELIMINARY MATCHUP CONTEXT", "completed game", "defenses represented", "full-PPR fantasy points allowed per completed game", "Early-season opponent results are unstable", "does not change the recommendation", "Authoritative Matchup Rank remains unavailable"):
        assert phrase in template
    for phrase in ("easiest", "hardest", "favorable", "unfavorable", "START", "SIT", "ADD", "DROP", "TRADE"):
        assert phrase not in template