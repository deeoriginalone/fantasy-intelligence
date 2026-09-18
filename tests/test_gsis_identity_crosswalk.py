import pytest

from services.gsis_identity_crosswalk import attach_opportunity_player_ids, resolve_gsis_crosswalk


SLEEPER_LINEAGE = {"source": "sleeper.players.nfl", "source_authority": "sleeper", "artifact_id": "players", "version": "2026-09-18", "retrieved_at": "2026-09-18T10:00:00Z"}
NFLVERSE_LINEAGE = {"source": "nflverse.players", "source_authority": "nflverse", "artifact_id": "players.csv", "version": "players", "checksum": "sha256:test", "retrieved_at": "2026-09-18T10:00:00Z"}


def sleeper(*ids):
    return [{"source_player_id": source_id, "gsis_id": gsis_id} for source_id, gsis_id in ids]


def nflverse(*ids):
    return [{"gsis_id": gsis_id} for gsis_id in ids]


def resolve(source, target, **kwargs):
    return resolve_gsis_crosswalk(source, target, sleeper_lineage=SLEEPER_LINEAGE, nflverse_lineage=NFLVERSE_LINEAGE, **kwargs)


def test_unique_gsis_resolves_to_opportunity_id_with_lineage():
    result = resolve(sleeper(("sleeper-1", "gsis-1")), nflverse("gsis-1"))
    mapping = result["mappings"][0]
    assert result["state"] == "AVAILABLE"
    assert mapping["state"] == "RESOLVED"
    assert mapping["opportunity_player_id"] == "gsis-1"
    assert mapping["lineage"]["nflverse"]["source_authority"] == "nflverse"
    assert mapping["decision_effect"] == "INFORMATIONAL_ONLY"


def test_missing_gsis_is_unresolved_without_name_fallback():
    result = resolve([{"source_player_id": "sleeper-1", "full_name": "Example Player"}], nflverse("gsis-1"))
    assert result["mappings"][0]["state"] == "UNRESOLVED"
    assert result["mappings"][0]["blockers"] == ["GSIS_IDENTITY_MISSING"]


def test_duplicate_sleeper_gsis_is_ambiguous():
    result = resolve(sleeper(("sleeper-1", "gsis-1"), ("sleeper-2", "gsis-1")), nflverse("gsis-1"))
    assert result["state"] == "BLOCKED"
    assert all(item["state"] == "AMBIGUOUS" for item in result["mappings"])
    assert "GSIS_SLEEPER_ID_DUPLICATE" in result["blockers"]


def test_duplicate_nflverse_gsis_is_ambiguous():
    result = resolve(sleeper(("sleeper-1", "gsis-1")), nflverse("gsis-1", "gsis-1"))
    assert result["mappings"][0]["state"] == "AMBIGUOUS"
    assert "GSIS_NFLVERSE_ID_DUPLICATE" in result["blockers"]


def test_missing_target_is_unresolved_and_missing_provenance_is_blocked():
    result = resolve(sleeper(("sleeper-1", "gsis-1")), nflverse("other"))
    assert result["mappings"][0]["state"] == "UNRESOLVED"
    assert "GSIS_OPPORTUNITY_ID_UNRESOLVED" in result["blockers"]
    blocked = resolve_gsis_crosswalk(sleeper(("sleeper-1", "gsis-1")), nflverse("gsis-1"), sleeper_lineage=SLEEPER_LINEAGE, nflverse_lineage={})
    assert blocked["state"] == "BLOCKED"
    assert any(item.startswith("GSIS_NFLVERSE_PROVENANCE_UNAVAILABLE") for item in blocked["blockers"])


def test_attach_only_adds_resolved_opportunity_ids_and_preserves_order():
    roster = [
        {"player": "A", "source_player_id": "sleeper-1", "sleeper_gsis_id": "gsis-1", "sleeper_metadata_retrieved_at": "2026-09-18T10:00:00Z"},
        {"player": "B", "source_player_id": "sleeper-2", "sleeper_gsis_id": None, "sleeper_metadata_retrieved_at": "2026-09-18T10:00:00Z"},
    ]
    attached = attach_opportunity_player_ids(roster, nflverse("gsis-1"), nflverse_lineage=NFLVERSE_LINEAGE)
    assert attached[0]["opportunity_player_id"] == "gsis-1"
    assert attached[0]["opportunity_identity_state"] == "RESOLVED"
    assert "opportunity_player_id" not in attached[1]
    assert attached[1]["opportunity_identity_state"] == "UNRESOLVED"


def test_no_name_or_local_serial_inference():
    result = resolve(
        [{"source_player_id": "sleeper-1", "gsis_id": None, "player_name": "Same Name", "local_player_id": 42}],
        [{"gsis_id": "gsis-1", "player_name": "Same Name"}],
    )
    assert result["mappings"][0]["state"] == "UNRESOLVED"
    assert result["mappings"][0]["opportunity_player_id"] is None


@pytest.mark.parametrize("field", ["source", "source_authority", "artifact_id", "version", "retrieved_at"])
def test_required_provenance_is_fail_closed(field):
    lineage = dict(NFLVERSE_LINEAGE)
    lineage[field] = None
    result = resolve_gsis_crosswalk(sleeper(("sleeper-1", "gsis-1")), nflverse("gsis-1"), sleeper_lineage=SLEEPER_LINEAGE, nflverse_lineage=lineage)
    assert result["state"] == "BLOCKED"
    assert f"GSIS_NFLVERSE_PROVENANCE_UNAVAILABLE:{field}" in result["blockers"]
