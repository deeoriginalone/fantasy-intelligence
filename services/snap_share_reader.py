"""Read-only access to published snap-share evidence."""
from __future__ import annotations
from typing import Any

COLUMNS = ("season", "week", "player_id", "pfr_player_id", "team", "opponent_team", "snap_share", "source", "source_authority", "source_recorded_at", "retrieved_at", "artifact_id", "version", "checksum", "freshness_threshold_id", "freshness_state", "completeness_state", "lineage", "publication_state")


def read_snap_share(connection: Any, *, player_id: Any, season: Any, week_start: Any = None, week_end: Any = None, limit: int = 3) -> dict[str, Any]:
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
    if not rows:
        base["blockers"] = ["SNAP_SHARE_READER_NO_ROWS"]
        return base
    current = rows[0]
    current_freshness = current.get("freshness_state")
    if current.get("snap_share") is None:
        base.update(state="UNAVAILABLE", rows=rows, blockers=["SNAP_SHARE_VALUE_UNAVAILABLE"], source=current.get("source"), freshness_state=current_freshness, completeness_state=current.get("completeness_state"), age=None, lineage=current.get("lineage"), freshness_threshold_id=current.get("freshness_threshold_id"))
        return base
    if current_freshness not in {"FRESH", "AGING"}:
        base.update(state="STALE", rows=rows, blockers=["SNAP_SHARE_EVIDENCE_STALE"], source=current.get("source"), freshness_state=current_freshness, completeness_state=current.get("completeness_state"), age=None, lineage=current.get("lineage"), freshness_threshold_id=current.get("freshness_threshold_id"))
        return base
    base.update(state="AVAILABLE", rows=rows, source=current.get("source"), freshness_state=current_freshness, completeness_state=current.get("completeness_state"), age=None, lineage=current.get("lineage"), freshness_threshold_id=current.get("freshness_threshold_id"))
    return base
