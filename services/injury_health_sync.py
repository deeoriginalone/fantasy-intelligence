"""Batch A.7 read-only injury status synchronization and health confidence.

The caller supplies an authoritative player-health snapshot and its verified
fetch timestamp. This module never fetches data, invents timestamps, writes to
a database, or submits fantasy transactions.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Mapping, Sequence

STATUS_VERIFIED = "VERIFIED"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNKNOWN = "UNKNOWN"

_HEALTHY = {"healthy", "active", "healthy / not listed", "not listed", "none"}
_OUT = {"out", "ir", "reserve-ret", "reserve/retired", "pup"}
_LIMITED = {"questionable", "doubtful", "probable", "limited", "day-to-day"}


def normalize_injury_status(value: Any) -> str:
    """Normalize known labels without treating missing evidence as healthy."""
    raw = str(value or "").strip()
    key = raw.lower()
    if not key or key == "unknown":
        return "Unknown"
    if key in _HEALTHY:
        return "Healthy"
    if key in _OUT:
        return "Out"
    if key in _LIMITED:
        return key.title()
    return raw


def injury_multiplier(status: Any) -> float:
    """Return a conservative availability multiplier for a verified status."""
    normalized = normalize_injury_status(status)
    if normalized == "Unknown":
        return 0.0
    if normalized == "Out":
        return 0.0
    if normalized == "Doubtful":
        return 0.25
    if normalized in {"Questionable", "Limited", "Day-To-Day"}:
        return 0.75
    if normalized == "Probable":
        return 0.90
    if normalized == "Healthy":
        return 1.0
    return 0.50


def synchronize_injury_statuses(
    roster: Sequence[Mapping[str, Any]] | None,
    player_health: Mapping[str, Mapping[str, Any]] | None,
    injury_fetched_at: datetime | str | None,
    *,
    player_id_field: str = "player_id",
) -> dict[str, Any]:
    """Overlay verified health evidence onto supplied roster rows.

    `player_health` must be keyed by the same stable player ID carried by each
    roster row. Missing IDs, missing mappings, missing statuses, and missing
    timestamp provenance fail closed. Existing roster dictionaries are copied.
    """
    rows = [dict(row) for row in (roster or [])]
    health = {str(k): v for k, v in (player_health or {}).items()}
    blockers: list[str] = []
    unresolved: list[str] = []
    invalid_indexes: list[int] = []
    synchronized: list[dict[str, Any]] = []

    if injury_fetched_at is None:
        blockers.append("INJURY_SNAPSHOT_TIMESTAMP_MISSING")
    if not isinstance(player_health, Mapping):
        blockers.append("AUTHORITATIVE_INJURY_SOURCE_MISSING")

    seen: Counter[str] = Counter()
    for index, row in enumerate(rows):
        player_id = str(row.get(player_id_field) or "").strip()
        if not player_id:
            invalid_indexes.append(index)
            item = dict(row)
            item.update({"injury_status": "Unknown", "injury_multiplier": 0.0,
                         "health_verified": False, "health_source_player_id": None})
            synchronized.append(item)
            continue
        seen[player_id] += 1
        source = health.get(player_id)
        raw_status = source.get("injury_status") if isinstance(source, Mapping) else None
        normalized = normalize_injury_status(raw_status)
        verified = normalized != "Unknown"
        if not verified:
            unresolved.append(player_id)
        item = dict(row)
        item.update({
            "injury_status": normalized,
            "injury_multiplier": injury_multiplier(normalized),
            "health_verified": verified,
            "health_source_player_id": player_id,
        })
        gaps = list(item.get("evidence_gaps") or [])
        if not verified and "INJURY_STATUS_UNRESOLVED" not in gaps:
            gaps.append("INJURY_STATUS_UNRESOLVED")
        item["evidence_gaps"] = gaps
        synchronized.append(item)

    duplicates = sorted(k for k, count in seen.items() if count > 1)
    if invalid_indexes:
        blockers.append("ROSTER_PLAYER_ID_MISSING")
    if duplicates:
        blockers.append("DUPLICATE_ROSTER_PLAYER_IDS")
    if unresolved:
        blockers.append("INJURY_STATUS_UNRESOLVED")

    blockers = sorted(set(blockers))
    if blockers:
        status = STATUS_UNKNOWN if any(x in blockers for x in (
            "INJURY_SNAPSHOT_TIMESTAMP_MISSING",
            "AUTHORITATIVE_INJURY_SOURCE_MISSING",
            "ROSTER_PLAYER_ID_MISSING",
            "DUPLICATE_ROSTER_PLAYER_IDS",
        )) else STATUS_PARTIAL
    else:
        status = STATUS_VERIFIED

    verified_count = sum(bool(row.get("health_verified")) for row in synchronized)
    total = len(synchronized)
    confidence = round(verified_count / total * 100) if total else 0
    if blockers:
        confidence = min(confidence, 50)

    return {
        "status": status,
        "allowed": status == STATUS_VERIFIED,
        "read_only": True,
        "injury_updated_at": injury_fetched_at,
        "freshness_metadata": {"injury_updated_at": injury_fetched_at},
        "player_count": total,
        "verified_health_players": verified_count,
        "unknown_health_players": total - verified_count,
        "health_confidence": {
            "score": confidence,
            "label": "HIGH" if confidence >= 80 else "MEDIUM" if confidence >= 60 else "LOW",
        },
        "unresolved_player_ids": sorted(set(unresolved)),
        "invalid_roster_row_indexes": invalid_indexes,
        "duplicate_player_ids": duplicates,
        "blockers": blockers,
        "players": synchronized,
    }
