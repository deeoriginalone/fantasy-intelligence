"""Fail-closed Sleeper GSIS to nflverse opportunity identity mapping."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

CROSSWALK_SCHEMA_VERSION = "gsis-opportunity-crosswalk.v1"
RESOLUTION_STATES = {"RESOLVED", "UNRESOLVED", "AMBIGUOUS", "CONTRADICTORY", "BLOCKED"}


def resolve_gsis_crosswalk(
    sleeper_records: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    nflverse_records: Sequence[Mapping[str, Any]],
    *,
    sleeper_lineage: Mapping[str, Any] | None,
    nflverse_lineage: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Resolve only the provider-supplied GSIS relationship."""
    result = {
        "schema_version": CROSSWALK_SCHEMA_VERSION,
        "state": "BLOCKED",
        "mappings": [],
        "blockers": [],
        "lineage": {"sleeper": dict(sleeper_lineage or {}), "nflverse": dict(nflverse_lineage or {})},
        "decision_effect": "INFORMATIONAL_ONLY",
    }
    provenance_blockers = _provenance_blockers(sleeper_lineage, "SLEEPER") + _provenance_blockers(nflverse_lineage, "NFLVERSE")
    if provenance_blockers:
        result["blockers"] = provenance_blockers
        return result

    sleeper_rows = _records(sleeper_records)
    nflverse_rows = list(nflverse_records or [])
    if not sleeper_rows:
        result["state"] = "UNAVAILABLE"
        result["blockers"] = ["GSIS_SLEEPER_SOURCE_EMPTY"]
        return result
    if not nflverse_rows:
        result["state"] = "UNAVAILABLE"
        result["blockers"] = ["GSIS_NFLVERSE_SOURCE_EMPTY"]
        return result

    nfl_by_gsis: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in nflverse_rows:
        gsis_id = _id(row.get("gsis_id"))
        if gsis_id:
            nfl_by_gsis[gsis_id].append(row)

    sleeper_by_gsis: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    mappings = []
    for row in sleeper_rows:
        source_player_id = _id(row.get("source_player_id") or row.get("player_id"))
        gsis_id = _id(row.get("gsis_id"))
        mapping = {
            "source_player_id": source_player_id,
            "source_identity_type": "sleeper_player_id",
            "gsis_id": gsis_id,
            "opportunity_player_id": None,
            "state": "UNRESOLVED",
            "blockers": [],
            "lineage": {"sleeper": dict(sleeper_lineage or {}), "nflverse": dict(nflverse_lineage or {})},
            "decision_effect": "INFORMATIONAL_ONLY",
        }
        if not source_player_id or not gsis_id:
            mapping["blockers"] = ["GSIS_IDENTITY_MISSING"]
            mappings.append(mapping)
            continue
        sleeper_by_gsis[gsis_id].append(mapping)
        candidates = nfl_by_gsis.get(gsis_id, [])
        if len(candidates) == 0:
            mapping["blockers"] = ["GSIS_OPPORTUNITY_ID_UNRESOLVED"]
        elif len(candidates) > 1:
            mapping["state"] = "AMBIGUOUS"
            mapping["blockers"] = ["GSIS_NFLVERSE_ID_DUPLICATE"]
        else:
            opportunity_id = _id(candidates[0].get("opportunity_player_id") or candidates[0].get("player_id") or candidates[0].get("gsis_id"))
            if not opportunity_id:
                mapping["blockers"] = ["GSIS_OPPORTUNITY_ID_MISSING"]
            else:
                mapping["opportunity_player_id"] = opportunity_id
        mappings.append(mapping)

    for gsis_id, group in sleeper_by_gsis.items():
        if len(group) > 1:
            for mapping in group:
                mapping["state"] = "AMBIGUOUS"
                mapping["opportunity_player_id"] = None
                mapping["blockers"] = ["GSIS_SLEEPER_ID_DUPLICATE"]

    for mapping in mappings:
        if mapping["state"] == "UNRESOLVED" and mapping["opportunity_player_id"]:
            mapping["state"] = "RESOLVED"
    resolved_ids = [item["opportunity_player_id"] for item in mappings if item["state"] == "RESOLVED"]
    if len(resolved_ids) != len(set(resolved_ids)):
        result["blockers"].append("GSIS_OPPORTUNITY_MAPPING_CONTRADICTORY")
        for mapping in mappings:
            if mapping["opportunity_player_id"] in resolved_ids:
                mapping["state"] = "CONTRADICTORY"
                mapping["opportunity_player_id"] = None
                mapping["blockers"] = ["GSIS_OPPORTUNITY_MAPPING_CONTRADICTORY"]

    result["mappings"] = mappings
    result["state"] = "AVAILABLE" if all(item["state"] == "RESOLVED" for item in mappings) else "BLOCKED"
    result["blockers"] = list(dict.fromkeys(result["blockers"] + [blocker for item in mappings for blocker in item["blockers"]]))
    result["lineage"]["input_count"] = len(sleeper_rows)
    result["lineage"]["mapping_count"] = len(mappings)
    result["lineage"]["reconciled"] = len(mappings) == len(sleeper_rows)
    if not result["lineage"]["reconciled"]:
        result["state"] = "BLOCKED"
        result["blockers"].append("GSIS_RECONCILIATION_MISMATCH")
    result["blockers"] = list(dict.fromkeys(result["blockers"]))
    return result


def attach_opportunity_player_ids(
    roster: Sequence[Mapping[str, Any]],
    nflverse_records: Sequence[Mapping[str, Any]],
    *,
    nflverse_lineage: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Add an opportunity ID only for a uniquely resolved roster GSIS identity."""
    sleeper_records = [
        {"source_player_id": player.get("source_player_id"), "gsis_id": player.get("sleeper_gsis_id")}
        for player in roster
    ]
    crosswalk = resolve_gsis_crosswalk(
        sleeper_records,
        nflverse_records,
        sleeper_lineage={
            "source": "sleeper.players.nfl",
            "source_authority": "sleeper",
            "artifact_id": "players.nfl",
            "version": "live-catalog",
            "retrieved_at": next((player.get("sleeper_metadata_retrieved_at") for player in roster if player.get("sleeper_metadata_retrieved_at")), None),
        },
        nflverse_lineage=nflverse_lineage,
    )
    attached = []
    for player, mapping in zip(roster, crosswalk["mappings"]):
        item = dict(player)
        if mapping["state"] == "RESOLVED":
            item["opportunity_player_id"] = mapping["opportunity_player_id"]
            item["opportunity_identity_state"] = "RESOLVED"
            item["opportunity_identity_lineage"] = mapping["lineage"]
        else:
            item.pop("opportunity_player_id", None)
            item["opportunity_identity_state"] = mapping["state"]
            item["opportunity_identity_blockers"] = mapping["blockers"]
        attached.append(item)
    return attached


def _records(records: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if isinstance(records, Mapping):
        return [{"source_player_id": key, **dict(value)} for key, value in records.items()]
    return list(records or [])


def _provenance_blockers(lineage: Mapping[str, Any] | None, label: str) -> list[str]:
    lineage = dict(lineage or {})
    required = ("source", "source_authority", "artifact_id", "version", "retrieved_at")
    return [f"GSIS_{label}_PROVENANCE_UNAVAILABLE:{field}" for field in required if not lineage.get(field)]


def _id(value: Any) -> str | None:
    value = str(value or "").strip()
    return value or None
