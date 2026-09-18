from services.nflverse_player_metadata import acquire_nflverse_player_metadata


PLAYERS = b"gsis_id,display_name\ngsis-1,Example Player\n"
TIMESTAMP = b"2026-09-18T08:00:00Z\n"


def test_metadata_acquisition_returns_rows_and_verified_lineage():
    def fetch(url):
        return PLAYERS if url.endswith("players.csv") else TIMESTAMP

    result = acquire_nflverse_player_metadata(fetch_bytes=fetch, retrieved_at="2026-09-18T10:00:00Z")
    assert result["state"] == "AVAILABLE"
    assert result["rows"] == [{"gsis_id": "gsis-1", "display_name": "Example Player"}]
    assert result["lineage"]["artifact_id"] == "nflverse.players.csv"
    assert result["lineage"]["version"] == "2026-09-18T08:00:00Z"
    assert result["lineage"]["checksum"]
    assert result["lineage"]["retrieved_at"] == "2026-09-18T10:00:00Z"


def test_metadata_retrieval_failure_blocks_without_rows():
    def fail(_url):
        raise RuntimeError("network unavailable")

    result = acquire_nflverse_player_metadata(fetch_bytes=fail, retrieved_at="2026-09-18T10:00:00Z")
    assert result["state"] == "BLOCKED"
    assert result["rows"] == []
    assert result["blockers"] == ["NFLVERSE_PLAYER_METADATA_RETRIEVAL_FAILED"]


def test_metadata_schema_and_version_fail_closed():
    def missing_gsis(url):
        return b"display_name\nExample Player\n" if url.endswith("players.csv") else TIMESTAMP

    def missing_version(url):
        return PLAYERS if url.endswith("players.csv") else b"\n"

    assert acquire_nflverse_player_metadata(fetch_bytes=missing_gsis)["blockers"] == ["NFLVERSE_PLAYER_METADATA_SCHEMA_UNVERIFIED"]
    assert acquire_nflverse_player_metadata(fetch_bytes=missing_version)["blockers"] == ["NFLVERSE_PLAYER_METADATA_VERSION_UNAVAILABLE"]
