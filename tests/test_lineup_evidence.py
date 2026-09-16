from services.lineup_evidence import build_lineup_evidence, build_matchup_evidence, build_projection_evidence

NOW = "2026-09-16T12:00:00+00:00"


def player(**updates):
    value = {
        "source_player_id": "sleeper-123",
        "local_player_id": 123,
        "position": "WR",
        "opponent": "KC",
        "projection": 120.0,
        "projection_source": "players.projected_points",
        "projection_retrieved_at": NOW,
        "projection_lineage": {"source": "players.projected_points"},
        "matchup_rank": 12,
        "matchup_source": "automated:nflverse",
        "matchup_retrieved_at": NOW,
        "matchup_lineage": {"source": "automated:nflverse", "version": "v1"},
    }
    value.update(updates)
    return value


def test_projection_preserves_identity_timestamps_and_explicit_source_blocker():
    result = build_projection_evidence(player(), season=2026, week=3, now=NOW)
    assert result["identity"] == {"source_player_id": "sleeper-123", "local_player_id": 123}
    assert result["season"] == 2026
    assert result["week"] == 3
    assert result["value"] == 120.0
    assert result["retrieved_at"] == NOW
    assert result["lineage"] == {"source": "players.projected_points"}
    assert result["freshness_state"] == "FRESH"
    assert "PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE" in result["blockers"]
    assert result["authoritative"] is False


def test_matchup_preserves_identity_context_and_unverified_threshold_blockers():
    result = build_matchup_evidence(player(), season=2026, week=3, now=NOW)
    assert result["identity"] == {"source_player_id": "sleeper-123", "local_player_id": 123}
    assert result["opponent_identity"] == "KC"
    assert result["position"] == "WR"
    assert result["scoring_context"] == "FULL_PPR"
    assert result["freshness_state"] == "FRESH"
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert "MATCHUP_POPULATION_UNVERIFIED" in result["blockers"]
    assert result["decision_effect"] == "NONE"


def test_published_metadata_is_preserved_without_upgrading_missing_authority():
    result = build_matchup_evidence(player(
        matchup_source_recorded_at=NOW,
        matchup_version="release-2026-w3",
        matchup_checksum="abc123",
        matchup_publication_lineage={"source": "nflverse", "artifact": "weekly.csv.gz"},
        matchup_sample_size=8,
        matchup_population="NFL WR opponents",
        matchup_directionality="LOWER_IS_HARDER",
        matchup_sample_threshold_id=None,
    ), season=2026, week=3, now=NOW)
    assert result["source_recorded_at"] == NOW
    assert result["version"] == "release-2026-w3"
    assert result["checksum"] == "abc123"
    assert result["lineage"] == {"source": "nflverse", "artifact": "weekly.csv.gz"}
    assert result["sample_size"] == 8
    assert result["comparison_population"] == "NFL WR opponents"
    assert result["rank_directionality"] == "LOWER_IS_HARDER"
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert "MATCHUP_POPULATION_UNVERIFIED" not in result["blockers"]
    assert "MATCHUP_DIRECTIONALITY_UNVERIFIED" not in result["blockers"]


def test_shared_lineup_evidence_preserves_partial_authority_and_blockers():
    projection = build_projection_evidence(player(), season=2026, week=3, now=NOW)
    matchup = build_matchup_evidence(player(), season=2026, week=3, now=NOW)
    result = build_lineup_evidence(projection, matchup)
    assert result["authoritative"] is False
    assert result["state"] == "BLOCKED"
    assert "PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE" in result["blockers"]
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert result["projection"]["lineage"] == projection["lineage"]
    assert result["matchup"]["lineage"] == matchup["lineage"]
    assert result["decision_effect"] == "NONE"


def test_missing_and_stale_evidence_fail_closed_without_values():
    missing = player(projection=None, projection_retrieved_at=None, matchup_source="Unavailable", matchup_retrieved_at=None)
    projection = build_projection_evidence(missing, season=2026, week=3, now=NOW)
    matchup = build_matchup_evidence(missing, season=2026, week=3, now=NOW)
    assert projection["value"] is None
    assert projection["freshness_state"] == "UNAVAILABLE"
    assert "PROJECTION_VALUE_UNAVAILABLE" in projection["blockers"]
    assert matchup["freshness_state"] == "UNAVAILABLE"
    assert "MATCHUP_SOURCE_UNAVAILABLE" in matchup["blockers"]
    stale = build_projection_evidence(player(projection_retrieved_at="2020-01-01T00:00:00+00:00"), season=2026, week=3, now=NOW)
    assert stale["freshness_state"] == "STALE"
    assert "PROJECTION_DATA_STALE" in stale["blockers"]


def test_identity_missing_is_blocked():
    result = build_matchup_evidence(player(source_player_id=None, local_player_id=None), season=2026, week=3, now=NOW)
    assert "MATCHUP_PLAYER_IDENTITY_UNAVAILABLE" in result["blockers"]
