import hashlib
import json

from services.dynastyprocess_identity_source import (
    ARTIFACT_ID,
    COMMIT_API_URL,
    LICENSE_ID,
    RAW_FILE_URL,
    SCHEMA_VERSION,
    acquire_dynastyprocess_identity_source,
)


VERSION = "b2a5e872b343fc36f819936ba6e0576e80519897"
RELEASED_AT = "2026-10-02T05:57:53Z"


def source_fixture(rows):
    payload = "sleeper_id,gsis_id,name\n" + "".join(
        f"{sleeper_id},{gsis_id},{name}\n" for sleeper_id, gsis_id, name in rows
    )
    return payload.encode()


def acquire_fixture(raw, *, release_version=VERSION):
    release = [{"sha": release_version, "commit": {"committer": {"date": RELEASED_AT}}}]
    responses = {
        COMMIT_API_URL: json.dumps(release).encode(),
        RAW_FILE_URL.format(version=release_version): raw,
    }
    requested = []

    def fetch(url):
        requested.append(url)
        return responses[url]

    result = acquire_dynastyprocess_identity_source(fetch_bytes=fetch, retrieved_at="2026-10-03T11:00:00Z")
    return result, requested


def test_source_acquisition_pins_release_checksum_and_completeness():
    raw = source_fixture([("sleeper-1", "gsis-1", "Name ignored")])
    result, requested = acquire_fixture(raw)
    mapping = result["mappings"][0]
    lineage = result["lineage"]
    assert result["state"] == "AVAILABLE"
    assert mapping["state"] == "RESOLVED"
    assert mapping["source_player_id"] == "sleeper-1"
    assert mapping["gsis_id"] == "gsis-1"
    assert requested == [COMMIT_API_URL, RAW_FILE_URL.format(version=VERSION)]
    assert lineage["artifact_id"] == ARTIFACT_ID
    assert lineage["version"] == VERSION
    assert lineage["source_recorded_at"] == RELEASED_AT
    assert lineage["retrieved_at"] == "2026-10-03T11:00:00Z"
    assert lineage["checksum"] == hashlib.sha256(raw).hexdigest()
    assert lineage["schema_version"] == SCHEMA_VERSION
    assert lineage["license"] == LICENSE_ID
    assert lineage["completeness_state"] == "COMPLETE"
    assert lineage["reconciliation"]["reconciled"] is True


def test_duplicate_and_contradictory_sleeper_ids_fail_closed():
    result, _ = acquire_fixture(source_fixture([
        ("same-pair", "gsis-1", "Ignored A"),
        ("same-pair", "gsis-1", "Ignored B"),
        ("conflict", "gsis-2", "Ignored C"),
        ("conflict", "gsis-3", "Ignored D"),
        ("missing-gsis", "", "Ignored E"),
    ]))
    mappings = {item["source_player_id"]: item for item in result["mappings"]}
    assert mappings["same-pair"]["state"] == "AMBIGUOUS"
    assert mappings["same-pair"]["gsis_id"] is None
    assert mappings["conflict"]["state"] == "CONTRADICTORY"
    assert mappings["conflict"]["gsis_id"] is None
    assert mappings["missing-gsis"]["state"] == "UNRESOLVED"
    assert result["lineage"]["reconciliation"]["duplicate_sleeper_id_count"] == 2
    assert result["lineage"]["reconciliation"]["contradictory_sleeper_id_count"] == 1


def test_source_schema_and_release_metadata_fail_closed():
    malformed = source_fixture([("sleeper-1", "gsis-1", "Name")]).replace(b"gsis_id", b"other_id")
    result, _ = acquire_fixture(malformed)
    assert result["state"] == "BLOCKED"
    assert result["blockers"] == ["DYNASTYPROCESS_IDENTITY_SCHEMA_UNVERIFIED"]

    invalid_version, _ = acquire_fixture(source_fixture([]), release_version="not-a-commit")
    assert invalid_version["state"] == "BLOCKED"
    assert invalid_version["blockers"] == ["DYNASTYPROCESS_RELEASE_METADATA_UNVERIFIED"]