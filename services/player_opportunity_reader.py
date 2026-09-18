"""Read-only access to published player-opportunity evidence."""
from __future__ import annotations

import json
from typing import Any, Mapping

from services.opportunity_evidence import (
    build_what_changed,
    published_opportunity_row_blockers,
)

READER_SCHEMA_VERSION = "player-opportunity-reader.v1"
TABLE_NAME = "player_opportunity_evidence"
COLUMNS = (
    "season", "week", "player_id", "team", "targets", "carries",
    "target_share", "carry_share", "touch_share", "snap_share",
    "route_participation", "red_zone_share", "role_classification", "source",
    "source_authority", "source_recorded_at", "retrieved_at", "artifact_id",
    "version", "checksum", "freshness_threshold_id", "freshness_state",
    "completeness_state", "lineage", "publication_state",
)


def read_player_opportunity(
    db_connection: Any,
    *,
    player_id: Any,
    season: Any,
    week: Any = None,
    week_start: Any = None,
    week_end: Any = None,
) -> dict[str, Any]:
    """Read validated published rows without mutating the database."""
    result = _base_result(player_id=player_id, season=season, week=week, week_start=week_start, week_end=week_end)
    scope_blockers = _scope_blockers(player_id, season, week, week_start, week_end)
    if scope_blockers:
        result["state"] = "BLOCKED"
        result["blockers"] = scope_blockers
        return result

    query, params = _select_query(player_id, season, week, week_start, week_end)
    connection = None
    cursor = None
    try:
        connection = db_connection() if callable(db_connection) else db_connection
        if connection is None or not hasattr(connection, "cursor"):
            raise RuntimeError("OPPORTUNITY_READER_CONNECTION_UNAVAILABLE")
        cursor = connection.cursor()
        cursor.execute(query, params)
        raw_rows = cursor.fetchall()
        rows = [_row_mapping(row, cursor.description) for row in raw_rows]
    except Exception:
        result["state"] = "BLOCKED"
        result["blockers"] = ["OPPORTUNITY_READER_QUERY_FAILED"]
        return result
    finally:
        if cursor is not None and hasattr(cursor, "close"):
            cursor.close()
        if connection is not None and callable(db_connection) and hasattr(connection, "close"):
            connection.close()

    normalized_rows = [_normalize_row(row) for row in rows]
    blockers = _scope_row_blockers(normalized_rows, player_id, season, week, week_start, week_end)
    for row in normalized_rows:
        blockers.extend(published_opportunity_row_blockers(row))
    blockers = list(dict.fromkeys(blockers))
    duplicate_weeks = _duplicate_weeks(normalized_rows)
    if duplicate_weeks:
        blockers.append("OPPORTUNITY_DUPLICATE_PLAYER_WEEK")
    if _contradictory_weeks(normalized_rows):
        blockers.append("OPPORTUNITY_CONTRADICTORY_PLAYER_WEEK")
    blockers = list(dict.fromkeys(blockers))
    result["rows"] = sorted(normalized_rows, key=lambda row: (row["week"], row["player_id"]))
    result["supported_weeks"] = sorted({row["week"] for row in normalized_rows})
    result["lineage"]["row_count"] = len(normalized_rows)
    if blockers:
        result["state"] = "BLOCKED"
        result["blockers"] = blockers
        return result
    if not normalized_rows:
        result["state"] = "UNAVAILABLE"
        result["blockers"] = ["OPPORTUNITY_READER_NO_ROWS"]
        return result
    result["state"] = "AVAILABLE"
    return result


def read_player_what_changed(
    db_connection: Any,
    *,
    player_id: Any,
    season: Any,
    week: Any = None,
    week_start: Any = None,
    week_end: Any = None,
) -> dict[str, Any]:
    """Adapt validated reader rows into the existing What Changed contract."""
    reader = read_player_opportunity(
        db_connection,
        player_id=player_id,
        season=season,
        week=week,
        week_start=week_start,
        week_end=week_end,
    )
    comparison = build_what_changed(
        None,
        None,
        None,
        published_weeks=reader["rows"] if reader["state"] == "AVAILABLE" else [],
        player_id=player_id,
        season=season,
        requested_week=week,
    )
    comparison["blockers"] = list(dict.fromkeys(reader["blockers"] + comparison["blockers"]))
    if reader["state"] != "AVAILABLE":
        comparison["state"] = reader["state"]
    comparison["reader_state"] = reader["state"]
    comparison["reader_lineage"] = reader["lineage"]
    comparison["decision_effect"] = "INFORMATIONAL_ONLY"
    return comparison


def _base_result(*, player_id: Any, season: Any, week: Any, week_start: Any, week_end: Any) -> dict[str, Any]:
    return {
        "schema_version": READER_SCHEMA_VERSION,
        "request_scope": {
            "player_id": player_id, "season": season, "week": week,
            "week_start": week_start, "week_end": week_end,
        },
        "state": "UNAVAILABLE",
        "rows": [],
        "supported_weeks": [],
        "blockers": [],
        "lineage": {"table": TABLE_NAME, "query_mode": "PARAMETERIZED_SELECT_ONLY"},
        "decision_effect": "INFORMATIONAL_ONLY",
    }


def _scope_blockers(player_id: Any, season: Any, week: Any, week_start: Any, week_end: Any) -> list[str]:
    blockers = []
    if not isinstance(player_id, str) or not player_id.strip():
        blockers.append("OPPORTUNITY_PLAYER_IDENTITY_INVALID")
    if not _positive_integer(season):
        blockers.append("OPPORTUNITY_SEASON_INVALID")
    if week is not None and not _positive_integer(week):
        blockers.append("OPPORTUNITY_WEEK_INVALID")
    if (week_start is None) != (week_end is None):
        blockers.append("OPPORTUNITY_WEEK_RANGE_INVALID")
    if week_start is not None and (not _positive_integer(week_start) or not _positive_integer(week_end) or week_start > week_end):
        blockers.append("OPPORTUNITY_WEEK_RANGE_INVALID")
    if week is not None and week_start is not None:
        blockers.append("OPPORTUNITY_SCOPE_AMBIGUOUS")
    return list(dict.fromkeys(blockers))


def _select_query(player_id: str, season: int, week: Any, week_start: Any, week_end: Any) -> tuple[str, tuple[Any, ...]]:
    query = (
        "SELECT " + ", ".join(COLUMNS) + " FROM player_opportunity_evidence "
        "WHERE player_id = %s AND season = %s"
    )
    params: list[Any] = [player_id, season]
    if week is not None:
        query += " AND week = %s"
        params.append(week)
    elif week_start is not None:
        query += " AND week BETWEEN %s AND %s"
        params.extend((week_start, week_end))
    query += " ORDER BY week ASC, player_id ASC"
    return query, tuple(params)


def _row_mapping(row: Any, description: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    names = [item[0] for item in (description or [])]
    return dict(zip(names, row))


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    normalized["target_volume"] = _number(row.get("targets"))
    normalized["carry_volume"] = _number(row.get("carries"))
    for field in ("target_share", "carry_share", "touch_share", "snap_share", "route_participation", "red_zone_share"):
        normalized[field] = _number(row.get(field))
    lineage = row.get("lineage")
    if isinstance(lineage, str):
        try:
            normalized["lineage"] = json.loads(lineage)
        except (TypeError, ValueError):
            normalized["lineage"] = lineage
    return normalized


def _scope_row_blockers(rows: list[Mapping[str, Any]], player_id: Any, season: Any, week: Any, week_start: Any, week_end: Any) -> list[str]:
    blockers = []
    for row in rows:
        if row.get("player_id") != player_id:
            blockers.append("OPPORTUNITY_PLAYER_IDENTITY_MISMATCH")
        if row.get("season") != season:
            blockers.append("OPPORTUNITY_SEASON_MISMATCH")
        if week is not None and row.get("week") != week:
            blockers.append("OPPORTUNITY_WEEK_MISMATCH")
        if week_start is not None and not week_start <= row.get("week", 0) <= week_end:
            blockers.append("OPPORTUNITY_WEEK_MISMATCH")
    return blockers


def _duplicate_weeks(rows: list[Mapping[str, Any]]) -> set[Any]:
    weeks = [row.get("week") for row in rows]
    return {week for week in weeks if weeks.count(week) > 1}


def _contradictory_weeks(rows: list[Mapping[str, Any]]) -> set[Any]:
    teams: dict[Any, set[Any]] = {}
    for row in rows:
        teams.setdefault(row.get("week"), set()).add(row.get("team"))
    return {week for week, values in teams.items() if len(values) > 1}


def _positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None