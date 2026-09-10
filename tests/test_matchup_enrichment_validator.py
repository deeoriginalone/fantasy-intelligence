from services.matchup_enrichment_validator import validate_matchup_enrichment

FRESH = {"matchup_updated_at": "2026-09-10T12:00:00+00:00"}


def row(name="A", **updates):
    value = {
        "player": name,
        "opponent": "X",
        "matchup_rank": 16,
        "matchup_modifier": 0.0,
        "is_bye": False,
    }
    value.update(updates)
    return value


def test_complete_matchup_is_verified():
    result = validate_matchup_enrichment([row()], FRESH)
    assert result["status"] == "VERIFIED"
    assert result["allowed"] is True
    assert result["coverage_score"] == 100
    assert result["matchup_updated_at"] == FRESH["matchup_updated_at"]


def test_empty_roster_fails_closed():
    result = validate_matchup_enrichment([], FRESH)
    assert result["status"] == "UNKNOWN"
    assert "MATCHUP_DATA_MISSING" in result["blockers"]


def test_missing_timestamp_fails_closed_without_invention():
    result = validate_matchup_enrichment([row()], {})
    assert result["status"] == "UNKNOWN"
    assert result["matchup_updated_at"] is None
    assert "MATCHUP_FRESHNESS_UNKNOWN" in result["blockers"]


def test_missing_opponent_is_partial_and_capped():
    result = validate_matchup_enrichment([row(opponent=None)], FRESH)
    assert result["status"] == "PARTIAL"
    assert result["missing_opponent_players"] == ["A"]
    assert result["coverage_confidence"]["score"] <= 50


def test_missing_rank_is_explicit():
    result = validate_matchup_enrichment([row(matchup_rank=None)], FRESH)
    assert "MATCHUP_RANK_MISSING" in result["blockers"]
    assert result["missing_rank_players"] == ["A"]


def test_missing_modifier_is_explicit_and_zero_is_valid():
    missing = validate_matchup_enrichment([row(matchup_modifier=None)], FRESH)
    neutral = validate_matchup_enrichment([row(matchup_modifier=0.0)], FRESH)
    assert "MATCHUP_MODIFIER_MISSING" in missing["blockers"]
    assert neutral["status"] == "VERIFIED"


def test_bye_week_does_not_require_matchup_fields():
    result = validate_matchup_enrichment(
        [row(is_bye=True, opponent=None, matchup_rank=None, matchup_modifier=None)],
        FRESH,
    )
    assert result["status"] == "VERIFIED"
    assert result["coverage_score"] == 100


def test_partial_coverage_reports_exact_players():
    result = validate_matchup_enrichment(
        [row("A"), row("B", matchup_rank=None), row("C", opponent=None)],
        FRESH,
    )
    assert result["coverage_score"] == 33
    assert result["missing_rank_players"] == ["B"]
    assert result["missing_opponent_players"] == ["C"]


def test_input_is_not_mutated():
    roster = [row()]
    original = [dict(roster[0])]
    validate_matchup_enrichment(roster, FRESH)
    assert roster == original
