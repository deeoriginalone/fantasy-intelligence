from datetime import datetime, timezone

from services.injury_health_sync import (
    injury_multiplier,
    normalize_injury_status,
    synchronize_injury_statuses,
)

TS = datetime(2026, 9, 10, tzinfo=timezone.utc)
ROSTER = [{"player_id": "1", "player": "A"}, {"player_id": "2", "player": "B"}]
HEALTH = {"1": {"injury_status": "active"}, "2": {"injury_status": "questionable"}}


def test_verified_snapshot_preserves_timestamp_and_statuses():
    result = synchronize_injury_statuses(ROSTER, HEALTH, TS)
    assert result["status"] == "VERIFIED"
    assert result["allowed"] is True
    assert result["injury_updated_at"] == TS
    assert result["freshness_metadata"]["injury_updated_at"] == TS
    assert [p["injury_status"] for p in result["players"]] == ["Healthy", "Questionable"]


def test_missing_timestamp_fails_closed_without_invention():
    result = synchronize_injury_statuses(ROSTER, HEALTH, None)
    assert result["status"] == "UNKNOWN"
    assert result["allowed"] is False
    assert result["injury_updated_at"] is None
    assert "INJURY_SNAPSHOT_TIMESTAMP_MISSING" in result["blockers"]


def test_missing_source_fails_closed():
    result = synchronize_injury_statuses(ROSTER, None, TS)
    assert result["status"] == "UNKNOWN"
    assert "AUTHORITATIVE_INJURY_SOURCE_MISSING" in result["blockers"]


def test_unmapped_health_is_partial_and_caps_confidence():
    result = synchronize_injury_statuses(ROSTER, {"1": HEALTH["1"]}, TS)
    assert result["status"] == "PARTIAL"
    assert result["allowed"] is False
    assert result["unresolved_player_ids"] == ["2"]
    assert result["health_confidence"]["score"] == 50
    assert "INJURY_STATUS_UNRESOLVED" in result["players"][1]["evidence_gaps"]


def test_missing_roster_player_id_fails_closed():
    result = synchronize_injury_statuses([{"player": "A"}], HEALTH, TS)
    assert result["status"] == "UNKNOWN"
    assert result["invalid_roster_row_indexes"] == [0]


def test_duplicate_ids_fail_closed():
    result = synchronize_injury_statuses([ROSTER[0], ROSTER[0]], HEALTH, TS)
    assert result["status"] == "UNKNOWN"
    assert result["duplicate_player_ids"] == ["1"]


def test_normalization_and_multipliers_are_conservative():
    assert normalize_injury_status("") == "Unknown"
    assert normalize_injury_status("IR") == "Out"
    assert injury_multiplier("Unknown") == 0.0
    assert injury_multiplier("Out") == 0.0
    assert injury_multiplier("Questionable") == 0.75
    assert injury_multiplier("Healthy") == 1.0


def test_input_rows_are_not_mutated():
    original = [dict(row) for row in ROSTER]
    synchronize_injury_statuses(ROSTER, HEALTH, TS)
    assert ROSTER == original
