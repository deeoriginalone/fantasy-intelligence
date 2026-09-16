from services.fantasypros_projection import (
    SOURCE,
    build_fantasypros_projection_contract,
    build_fantasypros_projection_evidence,
    fetch_fantasypros_projections,
    map_fantasypros_identity,
)

NOW = "2026-09-16T12:00:00+00:00"


def payload():
    return {
        "season": 2026,
        "week": 3,
        "players": [{
            "player_id": "fp-123",
            "position": "WR",
            "projection": 18.4,
            "projection_unit": "fantasy_points",
            "scoring_context": "FULL_PPR",
            "source_recorded_at": NOW,
        }],
    }


def test_fetch_captures_endpoint_params_and_api_key_without_persisting():
    seen = {}

    def transport(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return 200, __import__("json").dumps(payload()).encode()

    result = fetch_fantasypros_projections(
        season=2026, week=3, position="WR", player_id="fp-123",
        endpoint="https://provider.test/v2/projections", api_key="secret", transport=transport,
    )
    assert "season=2026" in seen["url"]
    assert "week=3" in seen["url"]
    assert "position=WR" in seen["url"]
    assert "player_id=fp-123" in seen["url"]
    assert seen["headers"]["X-API-Key"] == "secret"
    assert result["source"] == SOURCE
    assert result["authoritative"] is False
    assert result["decision_effect"] == "NONE"
    assert result["rows"][0]["player_id"] == "fp-123"


def test_rate_limit_is_explicit_and_fail_closed():
    result = fetch_fantasypros_projections(
        season=2026, week=3, endpoint="https://provider.test/v2", api_key="secret",
        transport=lambda url, headers: (429, b"{}"),
    )
    assert "FANTASYPROS_RATE_LIMITED" in result["blockers"]
    assert result["freshness_state"] == "UNAVAILABLE"
    assert result["authoritative"] is False


def test_contract_resolves_only_supplied_stable_provider_mapping():
    result = build_fantasypros_projection_contract(
        payload(), season=2026, week=3,
        player_mapping={"fp-123": [{"local_player_id": 7, "sleeper_player_id": "sleeper-123"}]},
        retrieved_at=NOW,
    )
    row = result["rows"][0]
    assert row["identity_mapping_state"] == "RESOLVED"
    assert row["identity_matches"][0]["local_player_id"] == 7
    assert row["provider_id"] == SOURCE
    assert row["provider_player_id"] == "fp-123"
    assert row["season"] == 2026 and row["week"] == 3
    assert row["source_recorded_at"] == NOW
    assert "PROJECTION_SOURCE_RECORDED_TIME_MISSING" not in row["blockers"]
    assert "PROJECTION_SOURCE_USE_UNVERIFIED" in result["blockers"]
    assert result["authoritative"] is False


def test_unresolved_and_ambiguous_identity_fail_closed():
    unresolved = build_fantasypros_projection_contract(payload(), season=2026, week=3, player_mapping={}, retrieved_at=NOW)
    ambiguous = build_fantasypros_projection_contract(
        payload(), season=2026, week=3,
        player_mapping={"fp-123": [{"local_player_id": 7}, {"local_player_id": 8}]}, retrieved_at=NOW,
    )
    assert unresolved["rows"][0]["identity_mapping_state"] == "UNRESOLVED"
    assert "PROJECTION_IDENTITY_UNRESOLVED" in unresolved["rows"][0]["blockers"]
    assert ambiguous["rows"][0]["identity_mapping_state"] == "AMBIGUOUS"
    assert "PROJECTION_IDENTITY_AMBIGUOUS" in ambiguous["rows"][0]["blockers"]


def test_mismatched_context_and_missing_contract_fields_remain_blocked():
    result = build_fantasypros_projection_contract(payload(), season=2025, week=4, player_mapping={"fp-123": [{"local_player_id": 7}]}, retrieved_at=NOW)
    assert "PROJECTION_SEASON_UNVERIFIED" in result["blockers"]
    assert "PROJECTION_WEEK_UNVERIFIED" in result["blockers"]
    row = result["rows"][0]
    assert row["identity_mapping_state"] == "RESOLVED"
    assert result["freshness_state"] == "UNAVAILABLE"
    assert "PROJECTION_FRESHNESS_THRESHOLD_UNVERIFIED" in result["blockers"]


def test_identity_mapping_resolves_explicit_provider_ids_only():
    result = map_fantasypros_identity(
        {"fpid": "fp-123", "mflid": "mfl-123", "team_id": "SEA", "position_id": "WR"},
        sleeper_records=[{"fpid": "fp-123", "sleeper_player_id": "sleeper-123"}],
        local_records=[{"fpid": "fp-123", "id": 7, "sleeper_player_id": "sleeper-123"}],
    )
    assert result["identity_state"] == "RESOLVED"
    assert result["provider_player_id"] == "fp-123"
    assert result["sleeper_player_id"] == "sleeper-123"
    assert result["local_player_id"] == 7
    assert result["identity_source"] == "explicit_provider_id"
    assert result["decision_effect"] == "NONE"
    assert result["schema_version"] == "fantasypros-identity.v1"


def test_identity_mapping_reports_unresolved_and_ambiguous_without_fallbacks():
    unresolved = map_fantasypros_identity({"fpid": "missing"}, sleeper_records=[], local_records=[])
    ambiguous = map_fantasypros_identity(
        {"fpid": "fp-123"},
        sleeper_records=[{"fpid": "fp-123", "sleeper_player_id": "s1"}, {"fpid": "fp-123", "sleeper_player_id": "s2"}],
        local_records=[{"fpid": "fp-123", "id": 7}],
    )
    assert unresolved["identity_state"] == "UNRESOLVED"
    assert "PROJECTION_IDENTITY_UNRESOLVED" in unresolved["blockers"]
    assert ambiguous["identity_state"] == "AMBIGUOUS"
    assert "PROJECTION_IDENTITY_AMBIGUOUS" in ambiguous["blockers"]


def test_identity_mapping_reports_contradictory_linkage():
    result = map_fantasypros_identity(
        {"fpid": "fp-123"},
        sleeper_records=[{"fpid": "fp-123", "sleeper_player_id": "s1"}],
        local_records=[{"fpid": "fp-123", "id": 7, "sleeper_player_id": "s2"}],
    )
    assert result["identity_state"] == "CONTRADICTORY"
    assert "PROJECTION_IDENTITY_CONTRADICTORY" in result["blockers"]


def test_non_authoritative_publication_preserves_supported_fields_and_gaps():
    identity = map_fantasypros_identity(
        {"fpid": "fp-123", "mflid": "mfl-123"},
        sleeper_records=[{"fpid": "fp-123", "sleeper_player_id": "s1"}],
        local_records=[{"fpid": "fp-123", "id": 7, "sleeper_player_id": "s1"}],
    )
    result = build_fantasypros_projection_evidence(
        {"fpid": "fp-123", "mflid": "mfl-123", "scoring": "PPR", "stats": {"points": 18.4}},
        season=2026, week=3, identity=identity, retrieved_at=NOW,
    )
    assert result["source"] == "fantasypros.api.v2"
    assert result["source_type"] == "automated"
    assert result["provider_player_id"] == "fp-123"
    assert result["provider_secondary_id"] == "mfl-123"
    assert result["identity_state"] == "RESOLVED"
    assert result["scoring_context"] == "PPR"
    assert result["scoring_authority_state"] == "VERIFIED"
    assert result["freshness_state"] == "UNAVAILABLE"
    assert result["authority_state"] == "NON_AUTHORITATIVE"
    assert result["decision_effect"] == "NONE"
    assert "PROJECTION_UNIT_UNVERIFIED" in result["blockers"]
    assert "PROJECTION_FRESHNESS_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert "PROJECTION_SOURCE_TIMESTAMP_UNAVAILABLE" in result["blockers"]


def test_non_authoritative_publication_blocks_unresolved_identity():
    result = build_fantasypros_projection_evidence(
        {"fpid": "missing", "scoring": "PPR", "projection_unit": "fantasy_points", "projection": 10},
        season=2026, week=3, retrieved_at=NOW,
    )
    assert result["identity_state"] == "UNRESOLVED"
    assert result["authority_state"] == "NON_AUTHORITATIVE"
    assert "PROJECTION_IDENTITY_UNRESOLVED" in result["blockers"]
    assert result["decision_effect"] == "NONE"
