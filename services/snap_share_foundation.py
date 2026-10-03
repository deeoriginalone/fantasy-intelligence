"""Snap-share foundation: parses and reconciles the real nflverse snap_counts
artifact without persisting or authorizing a value.

This module extends the player-role evidence domain (services.player_role_evidence)
without modifying that file. It reuses its shared constants (decision effect,
role-classification blocker) rather than duplicating the contract.

Verified against the real snap_counts_2026.csv artifact (season 2026, week 1,
1492 rows): offense_pct is a 0-1 ratio (observed range 0.0-1.0, never >1), every
row supplied pfr_player_id, offense_snaps, season, and week, and no duplicate or
multi-team (pfr_player_id, season, week) groups were observed in that sample.

No repository-owned pfr_player_id -> gsis_id/local-player crosswalk exists:
services/nflverse_identity_resolution.py and the `players` table only key on
gsis_id/name. identity_crosswalk therefore defaults to empty and every row
remains unresolved. This module never falls back to name matching for identity.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.player_role_evidence import DECISION_EFFECT, ROLE_CLASSIFICATION_BLOCKER
from services.integrity.integrity_service import snap_share_evidence_threshold, calculate_freshness

SNAP_COUNTS_ARTIFACT_ID = "snap_counts"
SNAP_SHARE_SCHEMA_VERSION = "nflverse-snap-share-foundation.v1"
SNAP_COUNTS_REQUIRED_COLUMNS = ("season", "week", "player", "pfr_player_id", "position", "team", "opponent")
OFFENSE_POSITIONS = {"QB", "RB", "WR", "TE", "FB", "HB", "OL", "G", "T", "C", "OT", "OG"}
DEFENSE_POSITIONS = {"DE", "DT", "NT", "DL", "LB", "CB", "DB", "S", "FS", "SS", "ILB", "OLB"}
SPECIAL_TEAMS_POSITIONS = {"K", "P", "LS"}


def _snap_share_value(raw_offense_pct: Any) -> tuple[float | None, str | None]:
    """Parse offense_pct as a verified 0-1 ratio; never rescale, invent, or default to zero."""
    if raw_offense_pct in (None, ""):
        return None, "SNAP_SHARE_VALUE_UNAVAILABLE"
    try:
        value = float(raw_offense_pct)
    except (TypeError, ValueError):
        return None, "SNAP_SHARE_VALUE_MALFORMED"
    if value < 0 or value > 1:
        return None, "SNAP_SHARE_SCALE_UNVERIFIED"
    return value, None


def _missing_field_blockers(row: Mapping[str, Any]) -> list[str]:
    reasons = []
    for field, blocker in (
        ("season", "SNAP_SHARE_SEASON_UNAVAILABLE"),
        ("week", "SNAP_SHARE_WEEK_UNAVAILABLE"),
        ("team", "SNAP_SHARE_TEAM_IDENTITY_UNAVAILABLE"),
        ("pfr_player_id", "SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE"),
        ("position", "SNAP_SHARE_PARTICIPATION_DOMAIN_UNAVAILABLE"),
    ):
        if row.get(field) in (None, ""):
            reasons.append(blocker)
    for field in ("player", "opponent"):
        if row.get(field) in (None, "") and "SNAP_SHARE_REQUIRED_COLUMN_MISSING" not in reasons:
            reasons.append("SNAP_SHARE_REQUIRED_COLUMN_MISSING")
    definition = _share_definition(row.get("position"))
    if definition is None and row.get("position") not in (None, ""):
        reasons.append("SNAP_SHARE_PARTICIPATION_DOMAIN_UNSUPPORTED")
    elif definition:
        _domain, count_field, percentage_field = definition
        for field in (count_field, percentage_field):
            if row.get(field) in (None, "") and "SNAP_SHARE_REQUIRED_COLUMN_MISSING" not in reasons:
                reasons.append("SNAP_SHARE_REQUIRED_COLUMN_MISSING")
    return reasons


def _share_definition(position: Any) -> tuple[str, str, str] | None:
    normalized = str(position or "").strip().upper()
    if normalized in OFFENSE_POSITIONS:
        return "OFFENSE", "offense_snaps", "offense_pct"
    if normalized in DEFENSE_POSITIONS:
        return "DEFENSE", "defense_snaps", "defense_pct"
    if normalized in SPECIAL_TEAMS_POSITIONS:
        return "SPECIAL_TEAMS", "st_snaps", "st_pct"
    return None


def normalize_snap_counts_batch(
    rows: Any,
    *,
    season: Any,
    source: str = "automated:nflverse",
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    checksum: str | None = None,
    version: str | None = None,
    identity_crosswalk: Mapping[str, Any] | None = None,
    threshold_environment: Mapping[str, str] | None = None,
    now: Any = None,
) -> dict[str, Any]:
    """Parse and reconcile one snap_counts artifact batch; never persists or scores it.

    identity_crosswalk, when supplied, must be a repository-owned mapping of
    pfr_player_id to a single stable player identity built only from
    already-authoritative repository data. No fuzzy or name-based matching is
    ever attempted here.
    """
    identity_crosswalk = dict(identity_crosswalk or {})
    input_row_count = len(rows)
    missing_field_count = 0
    unsupported_season_count = 0
    unsupported_position_count = 0
    eligible: list[dict[str, Any]] = []

    for row in rows:
        reasons = _missing_field_blockers(row)
        if reasons:
            missing_field_count += 1
            unsupported_position_count += int("SNAP_SHARE_PARTICIPATION_DOMAIN_UNSUPPORTED" in reasons)
            continue
        if str(row.get("season")) != str(season):
            unsupported_season_count += 1
            continue
        eligible.append(dict(row))

    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in eligible:
        key = (str(row["pfr_player_id"]), str(row["season"]), str(row["week"]), str(row["team"]))
        groups.setdefault(key, []).append(row)

    duplicate_row_count = 0
    contradictory_row_count = 0
    unresolved_identity_count = 0
    ambiguous_identity_count = 0
    contradictory_identity_count = 0
    preliminary: list[dict[str, Any]] = []

    for (pfr_player_id, group_season, group_week, team), group_rows in groups.items():
        if len(group_rows) > 1:
            signatures = {
                tuple(r.get(field) for field in ("position", "offense_snaps", "offense_pct", "defense_snaps", "defense_pct", "st_snaps", "st_pct"))
                for r in group_rows
            }
            if len(signatures) == 1:
                duplicate_row_count += len(group_rows) - 1
                eligible_row = group_rows[0]
            else:
                contradictory_row_count += len(group_rows)
                continue
        else:
            eligible_row = group_rows[0]

        row = eligible_row
        definition = _share_definition(row.get("position"))
        domain, count_field, percentage_field = definition
        snap_share, value_blocker = _snap_share_value(row.get(percentage_field))
        blockers = [value_blocker] if value_blocker else []

        resolution = identity_crosswalk.get(pfr_player_id)
        gsis_id = None
        state = "UNRESOLVED"
        if isinstance(resolution, (list, set, tuple)):
            if len(resolution) > 1:
                ambiguous_identity_count += 1
                blockers.append("SNAP_SHARE_PLAYER_IDENTITY_AMBIGUOUS")
                state = "AMBIGUOUS"
            elif len(resolution) == 1:
                gsis_id = next(iter(resolution))
                state = "RESOLVED"
            else:
                unresolved_identity_count += 1
                blockers.append("SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE")
        elif resolution:
            gsis_id = resolution
            state = "RESOLVED"
        else:
            unresolved_identity_count += 1
            blockers.append("SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE")

        preliminary.append({
            "gsis_id": gsis_id, "pfr_player_id": pfr_player_id, "player_name": row.get("player"),
            "season": group_season, "week": group_week, "team": team, "opponent": row.get("opponent"),
            "position": row.get("position"), "participation_domain": domain,
            "source_snap_count": row.get(count_field), "source_percentage_field": percentage_field,
            "snap_share": snap_share, "identity_resolution_state": state, "blockers": blockers,
        })

    # A single gsis_id claimed by more than one distinct pfr_id within this batch
    # is a real identity contradiction (one gsis_id cannot be two different
    # players); block every row involved instead of guessing which is correct.
    gsis_to_pfr_ids: dict[str, set[str]] = {}
    for row in preliminary:
        if row["gsis_id"]:
            gsis_to_pfr_ids.setdefault(row["gsis_id"], set()).add(row["pfr_player_id"])
    contradictory_gsis_ids = {gsis_id for gsis_id, pfr_ids in gsis_to_pfr_ids.items() if len(pfr_ids) > 1}

    normalized_rows: list[dict[str, Any]] = []
    for row in preliminary:
        if row["gsis_id"] in contradictory_gsis_ids:
            contradictory_identity_count += 1
            row["blockers"].append("SNAP_SHARE_PLAYER_IDENTITY_CONTRADICTORY")
            row["gsis_id"] = None
            row["identity_resolution_state"] = "CONTRADICTORY"
        row["identity_resolution_method"] = "repository_owned_pfr_crosswalk" if row["gsis_id"] else "none"
        row["resolved_player_id"] = row["gsis_id"]  # preserved alias for existing consumers/tests
        row["blockers"] = list(dict.fromkeys(row["blockers"]))
        row["authoritative"] = bool(row["gsis_id"] and row["snap_share"] is not None and not row["blockers"])
        normalized_rows.append(row)

    resolved_row_count = sum(1 for row in normalized_rows if row["authoritative"])
    excluded_row_count = missing_field_count + unsupported_season_count + duplicate_row_count + contradictory_row_count
    normalized_row_count = len(normalized_rows)
    reconciled = (normalized_row_count + excluded_row_count) == input_row_count

    reconciliation = {
        "input_row_count": input_row_count,
        "eligible_row_count": len(eligible),
        "resolved_row_count": resolved_row_count,
        "unresolved_identity_count": unresolved_identity_count,
        "ambiguous_identity_count": ambiguous_identity_count,
        "contradictory_identity_count": contradictory_identity_count,
        "duplicate_count": duplicate_row_count,
        "contradictory_count": contradictory_row_count,
        "malformed_metric_count": sum(1 for row in normalized_rows if "SNAP_SHARE_VALUE_MALFORMED" in row["blockers"]),
        "missing_field_count": missing_field_count,
        "unsupported_season_count": unsupported_season_count,
        "unsupported_position_count": unsupported_position_count,
        "excluded_row_count": excluded_row_count,
        "normalized_row_count": normalized_row_count,
        "reconciled": reconciled,
    }

    batch_blockers = []
    if not source or not str(source).startswith("automated:nflverse"):
        batch_blockers.append("SNAP_SHARE_SOURCE_UNAVAILABLE")
    if not retrieved_at:
        batch_blockers.append("SNAP_SHARE_RETRIEVAL_TIME_UNAVAILABLE")
    if not source_recorded_at:
        batch_blockers.append("SNAP_SHARE_SOURCE_RECORD_TIME_UNAVAILABLE")
    if not checksum:
        batch_blockers.append("SNAP_SHARE_CHECKSUM_UNAVAILABLE")
    threshold = snap_share_evidence_threshold(threshold_environment)
    freshness = calculate_freshness(
        {"snap_share_retrieved_at": retrieved_at, "snap_share_source": source},
        "snap_share", now=now, max_age_seconds=threshold.get("seconds"),
    ) if threshold.get("seconds") else {"status": "UNKNOWN", "age_seconds": None, "blocker": "SNAP_SHARE_FRESHNESS_THRESHOLD_BLOCKED" if threshold.get("state") == "BLOCKED" else "SNAP_SHARE_FRESHNESS_THRESHOLD_UNAVAILABLE"}
    if threshold.get("state") != "VERIFIED":
        batch_blockers.append(f"SNAP_SHARE_FRESHNESS_THRESHOLD_{threshold.get('state', 'UNAVAILABLE')}")
    elif freshness.get("status") in {"UNKNOWN", "STALE", "EXPIRED"}:
        batch_blockers.append(f"SNAP_SHARE_DATA_{freshness.get('status', 'UNAVAILABLE')}")
    if not reconciled:
        batch_blockers.append("SNAP_SHARE_BATCH_INCOMPLETE")
    if contradictory_row_count:
        batch_blockers.append("SNAP_SHARE_CONTRADICTORY_PLAYER_WEEK")
    batch_authoritative = not batch_blockers and resolved_row_count > 0
    if not batch_authoritative:
        for row in normalized_rows:
            row["authoritative"] = False

    if threshold.get("state") == "BLOCKED":
        freshness_state = "BLOCKED"
    elif freshness.get("status") in {"FRESH", "AGING"}:
        freshness_state = freshness["status"]
    elif freshness.get("status") in {"STALE", "EXPIRED"}:
        freshness_state = "STALE"
    else:
        freshness_state = "UNAVAILABLE"

    return {
        "season": season,
        "weeks": sorted({int(row["week"]) for row in rows if str(row.get("week") or "").isdigit()}),
        "rows": normalized_rows,
        "reconciliation": reconciliation,
        "freshness_state": freshness_state,
        "blockers": list(dict.fromkeys(batch_blockers)),
        "authoritative": batch_authoritative,
        "decision_effect": DECISION_EFFECT,
        "role_classification": None,
        "role_classification_blocker": ROLE_CLASSIFICATION_BLOCKER,
        "provenance": {
            "source": source,
            "source_authority": "automated" if str(source or "").startswith("automated:") else "UNVERIFIED",
            "source_recorded_at": source_recorded_at,
            "retrieved_at": retrieved_at,
            "artifact_identifier": SNAP_COUNTS_ARTIFACT_ID,
            "version": version,
            "checksum": checksum,
            "freshness_threshold_id": threshold.get("id"),
            "freshness_threshold_seconds": threshold.get("seconds"),
            "age": freshness.get("age_seconds"),
            "attribution": "NFLverse data, licensed under CC BY 4.0.",
            "completeness_state": "COMPLETE" if resolved_row_count == len(normalized_rows) and not missing_field_count and not unsupported_position_count and not unsupported_season_count and not contradictory_row_count and not ambiguous_identity_count and not contradictory_identity_count else "PARTIAL",
        },
        "schema_version": SNAP_SHARE_SCHEMA_VERSION,
    }
