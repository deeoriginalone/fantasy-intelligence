from pathlib import Path

import pytest

from services.pre_decision_snapshots import (
    SnapshotPersistenceError,
    SnapshotValidationError,
    build_pre_decision_snapshot,
    persist_snapshot,
    serialize_snapshot,
    snapshot_identity,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-09-16T12:00:00+00:00"


def make_snapshot(**updates):
    values = {
        "season": 2026,
        "week": 3,
        "decision_type": "WAIVER_REVIEW",
        "decision_subject": "player:123",
        "entity_identity": {"player_id": "123", "team": "SEA"},
        "decision_output": {"status": "MONITOR"},
        "evidence_state": "AVAILABLE",
        "evidence_source": {"name": "Sleeper", "record_type": "roster"},
        "evidence_lineage": {"source": "Sleeper", "record_id": "league:1:player:123"},
        "source_recorded_at": NOW,
        "retrieved_at": NOW,
        "freshness_state": "FRESH",
        "completeness_state": "COMPLETE",
        "confidence": {"level": "MEDIUM", "basis": "evidence"},
        "blockers": [],
        "captured_at": NOW,
    }
    values.update(updates)
    return build_pre_decision_snapshot(**values)


def test_snapshot_is_deterministic_and_has_stable_identity():
    first = make_snapshot()
    second = make_snapshot()
    assert first["snapshot_id"] == second["snapshot_id"] == snapshot_identity(first)
    assert serialize_snapshot(first) == serialize_snapshot(second)
    assert first["decision_effect"] == "NONE"


def test_snapshot_copies_decision_time_inputs_and_preserves_lineage():
    output = {"status": "START"}
    lineage = {"source": "Sleeper", "records": ["a"]}
    snapshot = make_snapshot(decision_output=output, evidence_lineage=lineage)
    output["status"] = "SIT"
    lineage["records"].append("hindsight")
    assert snapshot["decision_output"] == {"status": "START"}
    assert snapshot["evidence_lineage"] == {"source": "Sleeper", "records": ["a"]}
    assert snapshot["freshness_state"] == "FRESH"
    assert snapshot["completeness_state"] == "COMPLETE"


def test_missing_stale_and_incomplete_evidence_fail_closed_without_defaults():
    missing = make_snapshot(evidence_state="UNAVAILABLE", freshness_state="UNAVAILABLE", completeness_state="UNAVAILABLE")
    stale = make_snapshot(evidence_state="STALE", freshness_state="STALE", completeness_state="INCOMPLETE")
    assert missing["blockers"] == ["EVIDENCE_UNAVAILABLE"]
    assert stale["blockers"] == ["EVIDENCE_STALE"]
    assert missing["evidence_source"] == {"name": "Sleeper", "record_type": "roster"}
    assert missing["confidence"] == {"level": "MEDIUM", "basis": "evidence"}


def test_required_identity_and_effect_are_validated():
    with pytest.raises(SnapshotValidationError):
        make_snapshot(decision_subject="")
    invalid = make_snapshot()
    invalid["decision_effect"] = "START"
    with pytest.raises(SnapshotValidationError):
        serialize_snapshot(invalid)


class FakeCursor:
    def __init__(self, rowcount=1, error=None):
        self.rowcount = rowcount
        self.error = error
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        if self.error:
            raise self.error

    def close(self):
        pass


class FakeConnection:
    def __init__(self, rowcount=1, error=None):
        self.cursor_instance = FakeCursor(rowcount=rowcount, error=error)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_duplicate_capture_is_idempotent():
    connection = FakeConnection(rowcount=0)
    assert persist_snapshot(connection, make_snapshot()) is False
    assert connection.commits == 1
    assert "ON CONFLICT (snapshot_id) DO NOTHING" in connection.cursor_instance.calls[0][0]


def test_persistence_failure_is_explicit_and_does_not_change_snapshot():
    snapshot = make_snapshot()
    connection = FakeConnection(error=RuntimeError("database unavailable"))
    with pytest.raises(SnapshotPersistenceError):
        persist_snapshot(connection, snapshot)
    assert connection.rollbacks == 1
    assert snapshot == make_snapshot()


def test_migration_enforces_append_only_contract():
    sql = (ROOT / "migrations/014_pre_decision_snapshots.sql").read_text(encoding="utf-8")
    assert "BEFORE UPDATE OR DELETE" in sql
    assert "decision_effect = 'NONE'" in sql
    assert "ON CONFLICT" not in sql
    assert "snapshot_payload JSONB NOT NULL" in sql
