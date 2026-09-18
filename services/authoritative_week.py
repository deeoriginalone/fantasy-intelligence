"""Fail-closed ownership contract for fantasy week."""
from __future__ import annotations

from datetime import datetime, timezone
from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "authoritative-week.v1"
VALID_WEEKS = range(1, 19)
FRESHNESS_STATES = {"FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED"}
COMPLETENESS_STATES = {"COMPLETE", "INCOMPLETE", "UNAVAILABLE"}


def build_authoritative_week_contract(
    *,
    season: Any = None,
    week: Any = None,
    source: Any = None,
    source_authority: Any = None,
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    freshness_state: str = "UNAVAILABLE",
    completeness_state: str = "UNAVAILABLE",
    blockers: Any = None,
    lineage: Any = None,
) -> dict[str, Any]:
    normalized_freshness = _state(freshness_state, FRESHNESS_STATES)
    normalized_completeness = _state(completeness_state, COMPLETENESS_STATES)
    normalized_week = _week(week)
    normalized_season = _season(season)
    result = {
        "season": normalized_season,
        "week": normalized_week,
        "source": source,
        "source_authority": source_authority,
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "freshness_state": normalized_freshness,
        "completeness_state": normalized_completeness,
        "blockers": _blockers(blockers),
        "lineage": deepcopy(lineage),
        "schema_version": SCHEMA_VERSION,
    }
    if normalized_season is None:
        result["blockers"].append("WEEK_SEASON_UNAVAILABLE")
    if normalized_week is None:
        result["blockers"].append("WEEK_UNAVAILABLE")
    if source is None or source_authority is None:
        result["blockers"].append("WEEK_SOURCE_AUTHORITY_UNAVAILABLE")
    if retrieved_at is None:
        result["blockers"].append("WEEK_RETRIEVAL_TIME_UNAVAILABLE")
    if normalized_freshness in {"STALE", "UNAVAILABLE", "BLOCKED"}:
        result["blockers"].append(f"WEEK_FRESHNESS_{normalized_freshness}")
    if normalized_completeness != "COMPLETE":
        result["blockers"].append(f"WEEK_COMPLETENESS_{normalized_completeness}")
    result["blockers"] = list(dict.fromkeys(result["blockers"]))
    result["state"] = _contract_state(result)
    result["authoritative"] = result["state"] == "AVAILABLE"
    return result


def read_application_state_week(cur: Any, *, season: int, retrieved_at: Any = None) -> dict[str, Any]:
    """Read the persisted owner without accepting missing or mismatched state."""
    retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    try:
        cur.execute(
            "SELECT state_value, updated_at FROM application_state WHERE state_key='current_week'"
        )
        row = cur.fetchone()
    except Exception:
        return build_authoritative_week_contract(
            season=season,
            source="application_state",
            source_authority="application_state.current_week",
            freshness_state="BLOCKED",
            completeness_state="UNAVAILABLE",
            blockers=["CURRENT_WEEK_READ_FAILED"],
            lineage={"owner": "application_state.current_week"},
            retrieved_at=retrieved_at,
        )
    if not row or not isinstance(row[0], Mapping):
        return build_authoritative_week_contract(
            season=season,
            source="application_state",
            source_authority="application_state.current_week",
            freshness_state="UNAVAILABLE",
            completeness_state="UNAVAILABLE",
            blockers=["CURRENT_WEEK_STATE_UNAVAILABLE"],
            lineage={"owner": "application_state.current_week"},
            retrieved_at=retrieved_at,
        )
    state = dict(row[0])
    if _season(state.get("season")) != _season(season):
        return build_authoritative_week_contract(
            season=season,
            source="application_state",
            source_authority="application_state.current_week",
            source_recorded_at=row[1],
            retrieved_at=retrieved_at,
            freshness_state="BLOCKED",
            completeness_state="INCOMPLETE",
            blockers=["CURRENT_WEEK_SEASON_MISMATCH"],
            lineage={"owner": "application_state.current_week"},
        )
    return build_authoritative_week_contract(
        season=season,
        week=state.get("week"),
        source="application_state",
        source_authority="application_state.current_week",
        source_recorded_at=row[1],
        retrieved_at=retrieved_at,
        freshness_state="FRESH" if row[1] is not None else "UNAVAILABLE",
        completeness_state="COMPLETE",
        lineage={"owner": "application_state.current_week"},
    )


def resolve_week_owners(*owners: Mapping[str, Any]) -> dict[str, Any]:
    """Prefer valid Sleeper live state, then valid persisted state."""
    available = [owner for owner in owners if owner.get("authoritative")]
    weeks = {owner.get("week") for owner in available}
    sleeper = next((owner for owner in available if owner.get("source_authority") == "sleeper.state.nfl"), None)
    persisted = next((owner for owner in available if owner.get("source_authority") == "application_state.current_week"), None)
    result = dict(sleeper or persisted or build_authoritative_week_contract(blockers=["NO_AUTHORITATIVE_WEEK_OWNER"]))
    result.setdefault("warnings", [])
    result["owner_contracts"] = [dict(owner) for owner in owners]
    if sleeper and persisted:
        if sleeper.get("season") == persisted.get("season") and sleeper.get("week") == persisted.get("week"):
            result["authority_agreement"] = "AGREED"
            result["selected_owner"] = sleeper.get("source_authority")
        else:
            result["authority_agreement"] = "DISAGREEMENT"
            result["selected_owner"] = sleeper.get("source_authority")
            result["warnings"].append("PERSISTED_WEEK_CONFLICT")
            result["conflicting_owners"] = [
                {"source": owner.get("source"), "source_authority": owner.get("source_authority"), "season": owner.get("season"), "week": owner.get("week"), "source_recorded_at": owner.get("source_recorded_at"), "retrieved_at": owner.get("retrieved_at"), "freshness_state": owner.get("freshness_state"), "authoritative": owner.get("authoritative")}
                for owner in (sleeper, persisted)
            ]
    elif sleeper:
        result["authority_agreement"] = "SLEEPER_ONLY"
        result["selected_owner"] = sleeper.get("source_authority")
        result["warnings"].append("PERSISTED_WEEK_UNAVAILABLE")
    elif persisted:
        result["authority_agreement"] = "PERSISTED_FALLBACK"
        result["selected_owner"] = persisted.get("source_authority")
        result["warnings"].append("SLEEPER_WEEK_UNAVAILABLE")
    else:
        result["authority_agreement"] = "NONE"
        result["selected_owner"] = None
    if not available:
        result["authoritative"] = False
        result["week"] = None
    return result


def build_sleeper_week_contract(state: Any, *, season: int, retrieved_at: Any = None) -> dict[str, Any]:
    """Normalize Sleeper NFL state without accepting mismatched or missing state."""
    state = dict(state) if isinstance(state, Mapping) else {}
    season_matches = bool(state) and str(state.get("season")) == str(season)
    return build_authoritative_week_contract(
        season=season,
        week=state.get("week"),
        source="Sleeper NFL state",
        source_authority="sleeper.state.nfl",
        retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat(),
        freshness_state="FRESH" if season_matches else ("UNAVAILABLE" if not state else "BLOCKED"),
        completeness_state="COMPLETE" if season_matches else "INCOMPLETE",
        blockers=[] if season_matches else ["SLEEPER_NFL_STATE_UNAVAILABLE" if not state else "SLEEPER_NFL_SEASON_MISMATCH"],
        lineage={"owner": "sleeper.state.nfl"},
    )


def acquire_authoritative_week(
    db_connection: Any,
    sleeper_state_reader: Any,
    *,
    season: int,
    retrieved_at: Any = None,
) -> dict[str, Any]:
    """Acquire both configured week owners and resolve them before consumers run."""
    connection = None
    cursor = None
    try:
        connection = db_connection() if callable(db_connection) else db_connection
        cursor = connection.cursor() if hasattr(connection, "cursor") else connection
        application_owner = read_application_state_week(cursor, season=season, retrieved_at=retrieved_at)
    except Exception:
        application_owner = build_authoritative_week_contract(
            season=season,
            source="application_state",
            source_authority="application_state.current_week",
            retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat(),
            freshness_state="BLOCKED",
            completeness_state="UNAVAILABLE",
            blockers=["CURRENT_WEEK_READ_FAILED"],
            lineage={"owner": "application_state.current_week"},
        )
    finally:
        if cursor is not None and cursor is not connection and hasattr(cursor, "close"):
            cursor.close()
        if connection is not None and callable(db_connection) and hasattr(connection, "close"):
            connection.close()

    try:
        sleeper_state = sleeper_state_reader()
    except Exception:
        sleeper_state = None
    sleeper_owner = build_sleeper_week_contract(sleeper_state, season=season, retrieved_at=retrieved_at)
    result = resolve_week_owners(application_owner, sleeper_owner)
    result["lineage"] = {
        "acquisition_boundary": "services.authoritative_week.acquire_authoritative_week",
        "owners": [application_owner.get("lineage"), sleeper_owner.get("lineage")],
    }
    result["owner_contracts"] = [application_owner, sleeper_owner]
    return result


def _contract_state(result: Mapping[str, Any]) -> str:
    if result["freshness_state"] == "STALE":
        return "STALE"
    if result["freshness_state"] == "BLOCKED" or "CURRENT_WEEK_SEASON_MISMATCH" in result["blockers"]:
        return "BLOCKED"
    if result["freshness_state"] == "UNAVAILABLE":
        return "UNAVAILABLE"
    if result["blockers"] or result["completeness_state"] != "COMPLETE":
        return "INSUFFICIENT_EVIDENCE"
    return "AVAILABLE"


def _season(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _week(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value not in VALID_WEEKS:
        return None
    return value


def _state(value: Any, allowed: set[str]) -> str:
    normalized = str(value or "UNAVAILABLE").upper()
    return normalized if normalized in allowed else "BLOCKED"


def _blockers(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [str(item) for item in values if item is not None and str(item)]
