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
    requested_source_player_ids: Sequence[str] | None = None,
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

    all_sleeper_rows = _records(sleeper_records)
    requested = set(requested_source_player_ids or [row.get("source_player_id") for row in all_sleeper_rows])
    sleeper_rows = [row for row in all_sleeper_rows if _id(row.get("source_player_id") or row.get("player_id")) in requested]
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
    nfl_by_espn: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in nflverse_rows:
        gsis_id = _id(row.get("gsis_id"))
        if gsis_id:
            nfl_by_gsis[gsis_id].append(row)
        espn_id = _id(row.get("espn_id"))
        if espn_id:
            nfl_by_espn[espn_id].append(row)

    sleeper_by_gsis: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    sleeper_by_espn: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    all_sleeper_by_gsis: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    all_sleeper_by_espn: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in all_sleeper_rows:
        gsis_id = _id(row.get("gsis_id"))
        espn_id = _id(row.get("espn_id"))
        if gsis_id:
            all_sleeper_by_gsis[gsis_id].append(row)
        if espn_id:
            all_sleeper_by_espn[espn_id].append(row)
    mappings = []
    for row in sleeper_rows:
        source_player_id = _id(row.get("source_player_id") or row.get("player_id"))
        gsis_id = _id(row.get("gsis_id"))
        mapping = {
            "source_player_id": source_player_id,
            "source_identity_type": "sleeper_player_id",
            "gsis_id": gsis_id,
            "espn_id": _id(row.get("espn_id")),
            "opportunity_player_id": None,
            "resolution_authority": None,
            "state": "UNRESOLVED",
            "blockers": [],
            "lineage": {"sleeper": dict(sleeper_lineage or {}), "nflverse": dict(nflverse_lineage or {})},
            "decision_effect": "INFORMATIONAL_ONLY",
        }
        if not source_player_id:
            mapping["blockers"] = ["GSIS_IDENTITY_MISSING"]
            mappings.append(mapping)
            continue
        if gsis_id:
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
                    mapping["resolution_authority"] = "gsis_id"
                    if mapping["espn_id"] and len(nfl_by_espn.get(mapping["espn_id"], [])) == 1:
                        espn_target = _id(nfl_by_espn[mapping["espn_id"]][0].get("gsis_id"))
                        if espn_target and espn_target != gsis_id:
                            mapping["state"] = "CONTRADICTORY"
                            mapping["opportunity_player_id"] = None
                            mapping["blockers"] = ["GSIS_ESPN_TARGET_CONTRADICTORY"]
            mappings.append(mapping)
            continue
        espn_id = mapping["espn_id"]
        if not espn_id:
            mapping["blockers"] = ["GSIS_IDENTITY_MISSING"]
            mappings.append(mapping)
            continue
        sleeper_by_espn[espn_id].append(mapping)
        if not _lineage_complete(sleeper_lineage) or not _lineage_complete(nflverse_lineage):
            mapping["state"] = "BLOCKED"
            mapping["blockers"] = ["ESPN_CROSSWALK_COVERAGE_UNVERIFIED"]
        elif len(all_sleeper_by_espn[espn_id]) > 1:
            mapping["state"] = "AMBIGUOUS"
            mapping["blockers"] = ["ESPN_SLEEPER_ID_DUPLICATE"]
        elif len(nfl_by_espn.get(espn_id, [])) == 0:
            mapping["blockers"] = ["ESPN_OPPORTUNITY_ID_UNRESOLVED"]
        elif len(nfl_by_espn[espn_id]) > 1:
            mapping["state"] = "AMBIGUOUS"
            mapping["blockers"] = ["ESPN_NFLVERSE_ID_DUPLICATE"]
        else:
            opportunity_id = _id(nfl_by_espn[espn_id][0].get("gsis_id"))
            if not opportunity_id:
                mapping["blockers"] = ["ESPN_OPPORTUNITY_ID_MISSING"]
            else:
                mapping["opportunity_player_id"] = opportunity_id
                mapping["resolution_authority"] = "espn_id"
        mappings.append(mapping)

    for gsis_id, group in sleeper_by_gsis.items():
        if len(all_sleeper_by_gsis[gsis_id]) > 1:
            for mapping in group:
                mapping["state"] = "AMBIGUOUS"
                mapping["opportunity_player_id"] = None
                mapping["blockers"] = ["GSIS_SLEEPER_ID_DUPLICATE"]

    for espn_id, group in sleeper_by_espn.items():
        if len(all_sleeper_by_espn[espn_id]) > 1:
            for mapping in group:
                mapping["state"] = "AMBIGUOUS"
                mapping["opportunity_player_id"] = None
                mapping["blockers"] = ["ESPN_SLEEPER_ID_DUPLICATE"]

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
    sleeper_records: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Add an opportunity ID only for a uniquely resolved roster GSIS identity."""
    roster_records = [
        {"source_player_id": player.get("source_player_id"), "gsis_id": player.get("sleeper_gsis_id")}
        | {"espn_id": player.get("sleeper_espn_id")}
        for player in roster
    ]
    source_records = sleeper_records if sleeper_records is not None else roster_records
    crosswalk = resolve_gsis_crosswalk(
        source_records,
        nflverse_records,
        sleeper_lineage={
            "source": "sleeper.players.nfl",
            "source_authority": "sleeper",
            "artifact_id": "players.nfl",
            "version": "live-catalog",
            "retrieved_at": next((player.get("sleeper_metadata_retrieved_at") for player in roster if player.get("sleeper_metadata_retrieved_at")), None),
            "coverage_state": "COMPLETE" if all(player.get("sleeper_metadata_coverage_state") == "COMPLETE" for player in roster) else "UNVERIFIED",
        },
        nflverse_lineage=nflverse_lineage,
        requested_source_player_ids=[str(player.get("source_player_id")) for player in roster if player.get("source_player_id")],
    )
    mappings_by_source = {mapping.get("source_player_id"): mapping for mapping in crosswalk["mappings"]}
    attached = []
    for player in roster:
        mapping = mappings_by_source.get(str(player.get("source_player_id")), {"state": "UNRESOLVED", "blockers": ["GSIS_IDENTITY_MISSING"], "lineage": {}})
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


def _lineage_complete(lineage: Mapping[str, Any] | None) -> bool:
    return bool(lineage and lineage.get("coverage_state") == "COMPLETE")


def _id(value: Any) -> str | None:
    value = str(value or "").strip()
    return value or None
