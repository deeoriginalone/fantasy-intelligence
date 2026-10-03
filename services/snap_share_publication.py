"""Atomic publication of validated informational snap-share evidence."""
from __future__ import annotations
import json
import math
from typing import Any, Mapping

SUPPORTED = {"FRESH", "AGING"}


def _blocker(evidence: Mapping[str, Any]) -> str | None:
    provenance = evidence.get("provenance") or {}
    reconciliation = evidence.get("reconciliation") or {}
    if not str(provenance.get("source") or "").startswith("automated:nflverse"):
        return "SNAP_SHARE_SOURCE_UNAVAILABLE"
    if not provenance.get("source_recorded_at") or not provenance.get("retrieved_at") or not provenance.get("checksum"):
        return "SNAP_SHARE_SOURCE_METADATA_UNAVAILABLE"
    crosswalk = provenance.get("identity_crosswalk") or {}
    if not all(crosswalk.get(field) for field in ("source", "source_authority", "artifact_id", "version", "checksum", "source_recorded_at", "retrieved_at")):
        return "SNAP_SHARE_IDENTITY_PROVENANCE_UNAVAILABLE"
    if evidence.get("freshness_state") not in SUPPORTED:
        return "SNAP_SHARE_FRESHNESS_UNAVAILABLE"
    if not reconciliation.get("reconciled"):
        return "SNAP_SHARE_BATCH_INCOMPLETE"
    if reconciliation.get("contradictory_count"):
        return "SNAP_SHARE_CONTRADICTORY_PLAYER_WEEK"
    rows = [row for row in evidence.get("rows") or [] if row.get("authoritative")]
    if not rows:
        return "SNAP_SHARE_ROW_INCOMPLETE"
    for row in rows:
        try:
            share = float(row.get("snap_share"))
        except (TypeError, ValueError):
            return "SNAP_SHARE_ROW_INCOMPLETE"
        if not row.get("gsis_id") or not math.isfinite(share) or not 0 <= share <= 1:
            return "SNAP_SHARE_ROW_INVALID"
    return None


def publish_snap_share(conn: Any, evidence: Mapping[str, Any]) -> int:
    blocker = _blocker(evidence)
    if blocker:
        raise ValueError(blocker)
    provenance = evidence["provenance"]
    threshold_id = provenance.get("freshness_threshold_id")
    rows = [row for row in evidence["rows"] if row.get("authoritative")]
    cursor = conn.cursor()
    try:
        weeks = sorted({int(week) for week in evidence.get("weeks") or [row["week"] for row in rows]})
        cursor.execute("DELETE FROM snap_share_evidence WHERE season=%s AND week = ANY(%s) AND source='automated:nflverse'", (evidence["season"], weeks))
        for row in rows:
            cursor.execute(
                """INSERT INTO snap_share_evidence(
                    season, week, player_id, pfr_player_id, team, opponent_team, snap_share,
                    source, source_authority, source_recorded_at, retrieved_at, artifact_id,
                    version, checksum, freshness_threshold_id, freshness_state,
                    completeness_state, lineage, publication_state
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                ON CONFLICT (season, week, player_id) DO UPDATE SET
                    pfr_player_id=EXCLUDED.pfr_player_id, team=EXCLUDED.team,
                    opponent_team=EXCLUDED.opponent_team, snap_share=EXCLUDED.snap_share,
                    source=EXCLUDED.source, source_authority=EXCLUDED.source_authority,
                    source_recorded_at=EXCLUDED.source_recorded_at, retrieved_at=EXCLUDED.retrieved_at,
                    artifact_id=EXCLUDED.artifact_id, version=EXCLUDED.version, checksum=EXCLUDED.checksum,
                    freshness_threshold_id=EXCLUDED.freshness_threshold_id, freshness_state=EXCLUDED.freshness_state,
                    completeness_state=EXCLUDED.completeness_state, lineage=EXCLUDED.lineage,
                    publication_state=EXCLUDED.publication_state""",
                (row["season"], row["week"], row["gsis_id"], row["pfr_player_id"], row["team"], row.get("opponent"), row["snap_share"], provenance["source"], provenance["source_authority"], provenance.get("source_recorded_at"), provenance["retrieved_at"], provenance["artifact_identifier"], provenance.get("version"), provenance["checksum"], threshold_id, evidence["freshness_state"], "COMPLETE", json.dumps({**provenance, "sample": {"position": row.get("position"), "participation_domain": row.get("participation_domain"), "snap_count": row.get("source_snap_count"), "percentage_field": row.get("source_percentage_field")}, "reconciliation": evidence["reconciliation"]}), "PUBLISHED"),
            )
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
