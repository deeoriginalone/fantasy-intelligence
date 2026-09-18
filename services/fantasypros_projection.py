"""Non-authoritative FantasyPros projection discovery adapter."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE = "fantasypros.api.v2"
SCHEMA_VERSION = "fantasypros-projection-poc.v1"
DECISION_EFFECT = "NONE"
IDENTITY_SCHEMA_VERSION = "fantasypros-identity.v1"
PUBLICATION_SCHEMA_VERSION = "fantasypros-projection-evidence.v1"
AUTHORITY_BLOCKERS = {
    "PROJECTION_SOURCE_USE_UNVERIFIED": {
        "description": "Permitted provider use has not been verified for authoritative projection evidence.",
        "affected_capability": "projection_authority",
        "recommendation_impact": "Projection evidence remains informational and cannot support recommendations.",
        "authority_impact": "Blocks projection authority.",
    },
    "PROJECTION_UNIT_UNVERIFIED": {
        "description": "The provider-owned projection unit has not been verified.",
        "affected_capability": "projection_unit",
        "recommendation_impact": "Projected values cannot be safely interpreted for recommendation use.",
        "authority_impact": "Blocks projection authority.",
    },
    "PROJECTION_SOURCE_TIMESTAMP_UNAVAILABLE": {
        "description": "Provider source, publication, or update timestamp is unavailable.",
        "affected_capability": "projection_freshness",
        "recommendation_impact": "Projection freshness cannot be established for recommendations.",
        "authority_impact": "Blocks projection authority.",
    },
    "PROJECTION_FRESHNESS_THRESHOLD_UNVERIFIED": {
        "description": "No approved projection freshness threshold is owned by the repository.",
        "affected_capability": "projection_freshness",
        "recommendation_impact": "Projection evidence remains unavailable for authoritative recommendation use.",
        "authority_impact": "Blocks projection authority.",
    },
    "PROJECTION_LINEAGE_VERSION_UNAVAILABLE": {
        "description": "Provider version or release lineage is unavailable.",
        "affected_capability": "projection_lineage",
        "recommendation_impact": "Projection lineage cannot support authoritative recommendation evidence.",
        "authority_impact": "Blocks projection authority.",
    },
}


class FantasyProsProjectionError(RuntimeError):
    """The provider response could not be safely inspected."""


def fetch_fantasypros_projections(
    *,
    season: int,
    week: int,
    position: str | None = None,
    player_id: str | None = None,
    endpoint: str | None = None,
    api_key: str | None = None,
    transport: Callable[[str, Mapping[str, str]], tuple[int, bytes]] | None = None,
) -> dict[str, Any]:
    """Fetch one POC payload without persisting or authorizing projections."""
    endpoint = endpoint or os.getenv("FANTASYPROS_PROJECTIONS_ENDPOINT")
    api_key = api_key or os.getenv("FANTASYPROS_API_KEY")
    retrieved_at = datetime.now(timezone.utc).isoformat()
    if not endpoint or not api_key:
        return _response_contract(
            season=season, week=week, retrieved_at=retrieved_at, rows=[],
            blockers=["FANTASYPROS_ENDPOINT_OR_API_KEY_UNAVAILABLE"],
        )
    params = {"season": str(season), "week": str(week)}
    if position:
        params["position"] = position
    if player_id:
        params["player_id"] = player_id
    url = f"{endpoint}{'&' if '?' in endpoint else '?'}{urlencode(params)}"
    headers = {"Accept": "application/json", "X-API-Key": api_key}
    try:
        status, body = transport(url, headers) if transport else _http_get(url, headers)
    except Exception as exc:
        return _response_contract(season=season, week=week, retrieved_at=retrieved_at, rows=[], blockers=["FANTASYPROS_REQUEST_FAILED", str(exc)])
    if status == 429:
        return _response_contract(season=season, week=week, retrieved_at=retrieved_at, rows=[], blockers=["FANTASYPROS_RATE_LIMITED"])
    if status < 200 or status >= 300:
        return _response_contract(season=season, week=week, retrieved_at=retrieved_at, rows=[], blockers=["FANTASYPROS_HTTP_ERROR", f"FANTASYPROS_HTTP_{status}"])
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _response_contract(season=season, week=week, retrieved_at=retrieved_at, rows=[], blockers=["FANTASYPROS_RESPONSE_INVALID_JSON"])
    rows = payload.get("players") if isinstance(payload, Mapping) else None
    return _response_contract(season=season, week=week, retrieved_at=retrieved_at, rows=rows if isinstance(rows, list) else [], payload=payload, blockers=[] if isinstance(rows, list) else ["FANTASYPROS_PROJECTION_ROWS_UNAVAILABLE"])


def build_fantasypros_projection_contract(
    payload: Mapping[str, Any] | None,
    *,
    season: int,
    week: int,
    player_mapping: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    retrieved_at: Any = None,
) -> dict[str, Any]:
    """Normalize provider rows; this contract is never authoritative."""
    payload = dict(payload or {})
    rows = payload.get("players") if isinstance(payload.get("players"), list) else []
    mappings = player_mapping or {}
    blockers = []
    response_season = payload.get("season")
    response_week = payload.get("week")
    if response_season != season:
        blockers.append("PROJECTION_SEASON_UNVERIFIED")
    if response_week != week:
        blockers.append("PROJECTION_WEEK_UNVERIFIED")
    normalized = []
    for row in rows:
        provider_id = _provider_id(row)
        matches = list(mappings.get(provider_id) or [])
        identity_state = "RESOLVED" if len(matches) == 1 else "AMBIGUOUS" if len(matches) > 1 else "UNRESOLVED"
        row_blockers = [] if identity_state == "RESOLVED" else [f"PROJECTION_IDENTITY_{identity_state}"]
        normalized.append({
            "source": SOURCE,
            "provider_id": SOURCE,
            "provider_player_id": provider_id,
            "season": response_season,
            "week": response_week,
            "position": row.get("position"),
            "projection": row.get("projection"),
            "projection_unit": row.get("projection_unit"),
            "scoring_context": row.get("scoring_context"),
            "retrieved_at": retrieved_at,
            "source_recorded_at": row.get("source_recorded_at"),
            "identity_mapping_state": identity_state,
            "identity_matches": matches,
            "freshness_state": "UNAVAILABLE",
            "completeness_state": "INCOMPLETE",
            "lineage": {"source": SOURCE, "provider_player_id": provider_id},
            "blockers": row_blockers + _row_blockers(row),
            "schema_version": SCHEMA_VERSION,
            "decision_effect": DECISION_EFFECT,
        })
    return _response_contract(season=season, week=week, retrieved_at=retrieved_at, rows=normalized, payload=payload, blockers=blockers)


def map_fantasypros_identity(
    provider_row: Mapping[str, Any],
    *,
    sleeper_records: Sequence[Mapping[str, Any]] | None = None,
    local_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Map provider IDs only through explicit stable IDs; never use names."""
    provider_player_id = _provider_id(provider_row)
    provider_mfl_id = _provider_mfl_id(provider_row)
    sleeper_matches = _identity_matches(provider_player_id, provider_mfl_id, sleeper_records or (), "sleeper")
    local_matches = _identity_matches(provider_player_id, provider_mfl_id, local_records or (), "local")
    blockers = []
    if len(sleeper_matches) > 1 or len(local_matches) > 1:
        state = "AMBIGUOUS"
        blockers.append("PROJECTION_IDENTITY_AMBIGUOUS")
    elif len(sleeper_matches) != 1 or len(local_matches) != 1:
        state = "UNRESOLVED"
        blockers.append("PROJECTION_IDENTITY_UNRESOLVED")
    else:
        sleeper = sleeper_matches[0]
        local = local_matches[0]
        sleeper_id = _first_id(sleeper, ("sleeper_player_id", "sleeper_id", "player_id"))
        local_id = _first_id(local, ("local_player_id", "id", "player_id"))
        linked_sleeper_id = _first_id(local, ("sleeper_player_id", "sleeper_id"))
        if linked_sleeper_id and str(linked_sleeper_id) != str(sleeper_id):
            state = "CONTRADICTORY"
            blockers.append("PROJECTION_IDENTITY_CONTRADICTORY")
        else:
            state = "RESOLVED"
    return {
        "provider_player_id": provider_player_id,
        "provider_source": SOURCE,
        "sleeper_player_id": _first_id(sleeper_matches[0], ("sleeper_player_id", "sleeper_id", "player_id")) if len(sleeper_matches) == 1 else None,
        "local_player_id": _first_id(local_matches[0], ("local_player_id", "id", "player_id")) if len(local_matches) == 1 else None,
        "identity_state": state,
        "identity_source": "explicit_provider_id",
        "lineage": {"provider": {"fpid": provider_player_id, "mflid": provider_mfl_id}, "sleeper_matches": sleeper_matches, "local_matches": local_matches},
        "blockers": blockers,
        "schema_version": IDENTITY_SCHEMA_VERSION,
        "decision_effect": DECISION_EFFECT,
    }


def build_fantasypros_projection_evidence(
    provider_row: Mapping[str, Any],
    *,
    season: Any,
    week: Any,
    identity: Mapping[str, Any] | None = None,
    retrieved_at: Any = None,
) -> dict[str, Any]:
    """Publish informational provider evidence without granting authority."""
    identity = dict(identity or {})
    blockers = list(identity.get("blockers") or [])
    scoring = provider_row.get("scoring") or provider_row.get("scoring_context")
    unit = provider_row.get("projection_unit")
    source_recorded_at = provider_row.get("source_recorded_at")
    update_at = provider_row.get("updated_at") or provider_row.get("last_updated")
    if not scoring:
        blockers.append("PROJECTION_SCORING_CONTEXT_UNVERIFIED")
    if not unit:
        blockers.append("PROJECTION_UNIT_UNVERIFIED")
    if not source_recorded_at and not update_at:
        blockers.append("PROJECTION_SOURCE_TIMESTAMP_UNAVAILABLE")
    blockers.extend(("PROJECTION_FRESHNESS_THRESHOLD_UNVERIFIED", "PROJECTION_LINEAGE_VERSION_UNAVAILABLE"))
    if not identity or identity.get("identity_state") != "RESOLVED":
        blockers.append("PROJECTION_IDENTITY_UNRESOLVED")
    blockers = list(dict.fromkeys(blockers))
    return {
        "source": SOURCE,
        "source_type": "automated",
        "source_authority_state": "VERIFIED",
        "source_use_authority_state": "PARTIAL",
        "provider_player_id": identity.get("provider_player_id") or _provider_id(provider_row),
        "provider_secondary_id": _provider_mfl_id(provider_row),
        "sleeper_player_id": identity.get("sleeper_player_id"),
        "local_player_id": identity.get("local_player_id"),
        "identity_state": identity.get("identity_state", "UNRESOLVED"),
        "identity_method": identity.get("identity_source"),
        "identity_lineage": identity.get("lineage"),
        "identity_blockers": identity.get("blockers") or ["PROJECTION_IDENTITY_UNRESOLVED"],
        "season": season,
        "week": week,
        "scoring_context": scoring,
        "scoring_authority_state": "VERIFIED" if scoring else "UNAVAILABLE",
        "projection": provider_row.get("projection") or provider_row.get("stats"),
        "projection_value_authority_state": "PARTIAL" if provider_row.get("projection") is not None or provider_row.get("stats") else "UNAVAILABLE",
        "projection_unit": unit,
        "projection_unit_authority_state": "VERIFIED" if unit else "UNAVAILABLE",
        "source_recorded_at": source_recorded_at,
        "updated_at": update_at,
        "retrieved_at": retrieved_at,
        "timestamp_authority_state": "VERIFIED" if retrieved_at else "UNAVAILABLE",
        "age": None,
        "freshness_threshold_id": None,
        "freshness_state": "UNAVAILABLE",
        "freshness_authority_state": "UNAVAILABLE",
        "completeness_state": "COMPLETE" if not blockers else "INCOMPLETE",
        "lineage": {"provider": {"source": SOURCE, "provider_player_id": identity.get("provider_player_id") or _provider_id(provider_row), "provider_secondary_id": _provider_mfl_id(provider_row)}, "identity": identity.get("lineage"), "retrieval": {"retrieved_at": retrieved_at}},
        "lineage_state": "PARTIAL",
        "version": None,
        "blockers": blockers,
        "authority_blockers": [
            {"blocker_id": blocker, **AUTHORITY_BLOCKERS[blocker]}
            for blocker in blockers
            if blocker in AUTHORITY_BLOCKERS
        ],
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "authority_state": "NON_AUTHORITATIVE",
        "decision_effect": DECISION_EFFECT,
    }


def _response_contract(*, season: int, week: int, retrieved_at: Any, rows: list[Mapping[str, Any]], payload: Any = None, blockers: list[str]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "provider_id": SOURCE,
        "season": season,
        "week": week,
        "rows": rows,
        "payload": payload,
        "retrieved_at": retrieved_at,
        "source_recorded_at": None,
        "freshness_state": "UNAVAILABLE",
        "completeness_state": "COMPLETE" if rows and not blockers else "INCOMPLETE",
        "blockers": list(dict.fromkeys([*blockers, "PROJECTION_SOURCE_USE_UNVERIFIED", "PROJECTION_SOURCE_RETRIEVAL_TIME_MISSING", "PROJECTION_FRESHNESS_THRESHOLD_UNVERIFIED"])),
        "lineage": {"source": SOURCE, "retrieved_at": retrieved_at},
        "schema_version": SCHEMA_VERSION,
        "decision_effect": DECISION_EFFECT,
        "authoritative": False,
    }


def _provider_id(row: Mapping[str, Any]) -> str | None:
    value = row.get("provider_player_id") or row.get("fpid") or row.get("player_id") or row.get("fantasypros_player_id")
    return str(value) if value not in (None, "") else None


def _provider_mfl_id(row: Mapping[str, Any]) -> str | None:
    value = row.get("mflid") or row.get("mfl_id")
    return str(value) if value not in (None, "") else None


def _identity_matches(provider_id: str | None, mfl_id: str | None, records: Sequence[Mapping[str, Any]], kind: str) -> list[dict[str, Any]]:
    matches = []
    for record in records:
        provider_values = {str(record.get(key)) for key in ("fpid", "fantasypros_id", "fantasypros_player_id", "provider_player_id") if record.get(key) not in (None, "")}
        mfl_values = {str(record.get(key)) for key in ("mflid", "mfl_id") if record.get(key) not in (None, "")}
        if (provider_id and provider_id in provider_values) or (mfl_id and mfl_id in mfl_values):
            matches.append(dict(record))
    return matches


def _first_id(record: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if record.get(key) not in (None, ""):
            return record[key]
    return None


def _row_blockers(row: Mapping[str, Any]) -> list[str]:
    blockers = []
    if row.get("projection") is None:
        blockers.append("PROJECTION_VALUE_UNAVAILABLE")
    if not row.get("projection_unit"):
        blockers.append("PROJECTION_UNIT_UNVERIFIED")
    if not row.get("scoring_context"):
        blockers.append("PROJECTION_SCORING_CONTEXT_UNVERIFIED")
    if not row.get("source_recorded_at"):
        blockers.append("PROJECTION_SOURCE_RECORDED_TIME_MISSING")
    return blockers


def _http_get(url: str, headers: Mapping[str, str]) -> tuple[int, bytes]:
    request = Request(url, headers=dict(headers), method="GET")
    with urlopen(request, timeout=20) as response:
        return response.status, response.read()
