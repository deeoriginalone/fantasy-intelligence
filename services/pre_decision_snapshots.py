"""Immutable, fail-closed capture of evidence available before a decision."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

SNAPSHOT_SCHEMA_VERSION = "pre-decision-snapshot.v1"
DECISION_EFFECT = "NONE"
EVIDENCE_STATES = {"AVAILABLE", "UNAVAILABLE", "BLOCKED", "STALE", "INSUFFICIENT_EVIDENCE"}
FRESHNESS_STATES = {"FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED"}
COMPLETENESS_STATES = {"COMPLETE", "INCOMPLETE", "UNAVAILABLE"}


class SnapshotValidationError(ValueError):
    """The supplied decision-time record cannot be captured safely."""


class SnapshotPersistenceError(RuntimeError):
    """The database could not append a snapshot."""


def build_pre_decision_snapshot(
    *,
    season: int,
    week: int,
    decision_type: str,
    decision_subject: str,
    decision_output: Any,
    evidence_state: str = "UNAVAILABLE",
    evidence_source: Any = None,
    evidence_lineage: Any = None,
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    freshness_state: str = "UNAVAILABLE",
    completeness_state: str = "UNAVAILABLE",
    confidence: Any = None,
    blockers: Any = None,
    captured_at: Any = None,
    entity_identity: Any = None,
) -> dict[str, Any]:
    """Build a self-contained record without deriving or upgrading evidence."""
    if isinstance(season, bool) or not isinstance(season, int) or season < 0:
        raise SnapshotValidationError("season must be a non-negative integer")
    if isinstance(week, bool) or not isinstance(week, int) or week < 0:
        raise SnapshotValidationError("week must be a non-negative integer")
    decision_type = str(decision_type or "").strip()
    decision_subject = str(decision_subject or "").strip()
    if not decision_type or not decision_subject:
        raise SnapshotValidationError("decision type and subject are required")

    evidence_state = _supported_state(evidence_state, EVIDENCE_STATES, "EVIDENCE_STATE_UNSUPPORTED")
    freshness_state = _supported_state(freshness_state, FRESHNESS_STATES, "FRESHNESS_STATE_UNSUPPORTED")
    completeness_state = _supported_state(completeness_state, COMPLETENESS_STATES, "COMPLETENESS_STATE_UNSUPPORTED")
    normalized_blockers = _blockers(blockers)
    if evidence_state != "AVAILABLE" and not normalized_blockers:
        normalized_blockers = [f"EVIDENCE_{evidence_state}"]
    if freshness_state in {"STALE", "UNAVAILABLE", "BLOCKED"} and not normalized_blockers:
        normalized_blockers = [f"FRESHNESS_{freshness_state}"]
    if completeness_state != "COMPLETE" and not normalized_blockers:
        normalized_blockers = [f"COMPLETENESS_{completeness_state}"]

    snapshot = {
        "snapshot_id": None,
        "season": season,
        "week": week,
        "decision_type": decision_type,
        "decision_subject": decision_subject,
        "entity_identity": deepcopy(entity_identity),
        "decision_output": deepcopy(decision_output),
        "evidence_state": evidence_state,
        "evidence_source": deepcopy(evidence_source),
        "evidence_lineage": deepcopy(evidence_lineage),
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "freshness_state": freshness_state,
        "completeness_state": completeness_state,
        "confidence": deepcopy(confidence),
        "blockers": normalized_blockers,
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "decision_effect": DECISION_EFFECT,
    }
    snapshot["snapshot_id"] = snapshot_identity(snapshot)
    return snapshot


def serialize_snapshot(snapshot: Mapping[str, Any]) -> str:
    """Serialize a snapshot deterministically for storage, hashing, and audit."""
    return _canonical(_normalized_snapshot(snapshot))


def snapshot_identity(snapshot: Mapping[str, Any]) -> str:
    """Return a stable identity for the decision and its decision-time evidence."""
    value = _normalized_snapshot(snapshot)
    value.pop("snapshot_id", None)
    value.pop("captured_at", None)
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def persist_snapshot(conn: Any, snapshot: Mapping[str, Any]) -> bool:
    """Append one snapshot; duplicate identities are an idempotent no-op."""
    normalized = _normalized_snapshot(snapshot)
    expected_id = snapshot_identity(normalized)
    if normalized.get("snapshot_id") != expected_id:
        raise SnapshotValidationError("snapshot_id does not match immutable snapshot content")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO pre_decision_snapshots(
                snapshot_id, season, week, decision_type, decision_subject,
                entity_identity, decision_output, evidence_state, evidence_source,
                evidence_lineage, source_recorded_at, retrieved_at, freshness_state,
                completeness_state, confidence, blockers, captured_at,
                schema_version, decision_effect, snapshot_payload
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb,
                      %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s,
                      %s, %s, %s::jsonb)
            ON CONFLICT (snapshot_id) DO NOTHING
            """,
            (
                normalized["snapshot_id"], normalized["season"], normalized["week"],
                normalized["decision_type"], normalized["decision_subject"],
                _json(normalized["entity_identity"]), _json(normalized["decision_output"]),
                normalized["evidence_state"], _json(normalized["evidence_source"]),
                _json(normalized["evidence_lineage"]), normalized["source_recorded_at"],
                normalized["retrieved_at"], normalized["freshness_state"],
                normalized["completeness_state"], _json(normalized["confidence"]),
                _json(normalized["blockers"]), normalized["captured_at"],
                normalized["schema_version"], normalized["decision_effect"],
                serialize_snapshot(normalized),
            ),
        )
        conn.commit()
        return cursor.rowcount == 1
    except Exception as exc:
        conn.rollback()
        raise SnapshotPersistenceError("pre-decision snapshot write failed") from exc
    finally:
        cursor.close()


def _normalized_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise SnapshotValidationError("snapshot must be a mapping")
    result = deepcopy(dict(snapshot))
    if result.get("decision_effect") != DECISION_EFFECT:
        raise SnapshotValidationError("decision_effect must remain NONE")
    result.setdefault("schema_version", SNAPSHOT_SCHEMA_VERSION)
    return result


def _supported_state(value: Any, allowed: set[str], blocker: str) -> str:
    normalized = str(value or "UNAVAILABLE").upper()
    return normalized if normalized in allowed else "BLOCKED"


def _blockers(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [str(item) for item in values if item is not None and str(item)]


def _json(value: Any) -> str:
    return _canonical(value)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
