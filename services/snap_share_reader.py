"""Read-only access to published snap-share evidence."""
from __future__ import annotations
import json
import os
from typing import Any

from services.integrity.integrity_service import calculate_freshness, snap_share_evidence_threshold

COLUMNS = ("season", "week", "player_id", "pfr_player_id", "team", "opponent_team", "snap_share", "source", "source_authority", "source_recorded_at", "retrieved_at", "artifact_id", "version", "checksum", "freshness_threshold_id", "freshness_state", "completeness_state", "lineage", "publication_state")


def read_snap_share(connection: Any, *, player_id: Any, season: Any, week_start: Any = None, week_end: Any = None, limit: int = 3, now: Any = None, threshold_environment: Any = None) -> dict[str, Any]:
    base = {"schema_version": "snap-share-reader.v1", "state": "UNAVAILABLE", "rows": [], "blockers": [], "authority_state": "INFORMATIONAL_ONLY", "decision_effect": "NONE"}
    if not isinstance(player_id, str) or not player_id.strip():
        base.update(blockers=["SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE"])
        return base
    if not isinstance(season, int) or season <= 0:
        base.update(state="BLOCKED", blockers=["SNAP_SHARE_SEASON_UNAVAILABLE"])
        return base
    try:
        cursor = connection.cursor()
    except Exception:
        base.update(state="BLOCKED", blockers=["SNAP_SHARE_READER_CONNECTION_UNAVAILABLE"])
        return base
    try:
        query = "SELECT " + ", ".join(COLUMNS) + " FROM snap_share_evidence WHERE player_id=%s AND season=%s"
        params = [player_id, season]
        if week_start is not None and week_end is not None:
            query += " AND week BETWEEN %s AND %s"
            params.extend((week_start, week_end))
        query += " ORDER BY week DESC LIMIT %s"
        params.append(limit)
        cursor.execute(query, tuple(params))
        rows = [dict(zip(COLUMNS, row)) if not isinstance(row, dict) else dict(row) for row in cursor.fetchall()]
    except Exception:
        base.update(state="BLOCKED", blockers=["SNAP_SHARE_READER_QUERY_FAILED"])
        return base
    finally:
        cursor.close()
    for row in rows:
        lineage = row.get("lineage")
        if isinstance(lineage, str):
            try:
                lineage = json.loads(lineage)
            except (TypeError, ValueError):
                lineage = {}
        sample = (lineage or {}).get("sample") or {}
        row["sample"] = sample
        row["position"] = sample.get("position")
        row["participation_domain"] = sample.get("participation_domain")
        row["source_snap_count"] = sample.get("snap_count")
        row["source_percentage_field"] = sample.get("percentage_field")
    threshold = snap_share_evidence_threshold(os.environ if threshold_environment is None else threshold_environment)
    if threshold.get("state") != "VERIFIED" or not threshold.get("seconds"):
        base.update(state="BLOCKED", rows=rows, blockers=["SNAP_SHARE_FRESHNESS_THRESHOLD_UNVERIFIED"])
        return base
    for row in rows:
        persisted = row.get("freshness_state")
        current = calculate_freshness(
            {"snap_share_retrieved_at": row.get("retrieved_at")},
            "snap_share",
            now=now,
            max_age_seconds=threshold["seconds"],
        )
        state = current.get("status")
        if state in {"FRESH", "AGING"} and persisted not in {"FRESH", "AGING"}:
            state = persisted
        if state == "EXPIRED":
            state = "STALE"
        row["persisted_freshness_state"] = persisted
        row["freshness_state"] = state
        row["age_seconds"] = current.get("age_seconds")
        row["freshness_blocker"] = current.get("blocker")
        row["freshness_threshold_id"] = threshold.get("id")
        row["freshness_threshold_seconds"] = threshold.get("seconds")
    if not rows:
        base["blockers"] = ["SNAP_SHARE_READER_NO_ROWS"]
        return base
    current = rows[0]
    current_freshness = current.get("freshness_state")
    if current.get("snap_share") is None:
        base.update(state="UNAVAILABLE", rows=rows, blockers=["SNAP_SHARE_VALUE_UNAVAILABLE"], source=current.get("source"), freshness_state=current_freshness, completeness_state=current.get("completeness_state"), age=None, lineage=current.get("lineage"), freshness_threshold_id=current.get("freshness_threshold_id"))
        return base
    if current_freshness not in {"FRESH", "AGING"}:
        state = "STALE" if current_freshness == "STALE" else "BLOCKED"
        blocker = "SNAP_SHARE_EVIDENCE_STALE" if current_freshness == "STALE" else current.get("freshness_blocker") or "SNAP_SHARE_RETRIEVAL_TIME_UNAVAILABLE"
        base.update(state=state, rows=rows, blockers=[blocker], source=current.get("source"), freshness_state=current_freshness, completeness_state=current.get("completeness_state"), age=current.get("age_seconds"), lineage=current.get("lineage"), freshness_threshold_id=current.get("freshness_threshold_id"))
        return base
    base.update(state="AVAILABLE", rows=rows, source=current.get("source"), freshness_state=current_freshness, completeness_state=current.get("completeness_state"), age=current.get("age_seconds"), lineage=current.get("lineage"), freshness_threshold_id=current.get("freshness_threshold_id"))
    return base
