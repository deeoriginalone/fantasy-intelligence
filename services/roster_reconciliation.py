"""Read-only roster reconciliation for Batch A.5.

This module compares authoritative local roster rows with a supplied Sleeper
roster payload. It never changes local data and never submits transactions.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
import re

STATUS_MATCHED = "MATCHED"
STATUS_DIVERGENT = "DIVERGENT"
STATUS_UNKNOWN = "UNKNOWN"

_SUFFIX_RE = re.compile(r"(?:jr|sr|ii|iii|iv)$", re.IGNORECASE)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")


def normalize_player_name(value: Any) -> str:
    """Return the repository-compatible comparison key for a player name."""
    normalized = _NON_ALNUM_RE.sub("", str(value or "").strip().lower())
    return _SUFFIX_RE.sub("", normalized)


def _local_name(row: Any) -> str:
    if isinstance(row, Mapping):
        return str(row.get("player_name") or row.get("name") or "").strip()
    if isinstance(row, (list, tuple)) and len(row) >= 2:
        return str(row[1] or "").strip()
    return ""


def _sleeper_player_ids(sleeper_roster: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(sleeper_roster, Mapping):
        return []
    raw = sleeper_roster.get("players")
    if not isinstance(raw, (list, tuple, set)):
        return []
    return [str(player_id) for player_id in raw if player_id is not None and str(player_id)]


def reconcile_roster(
    local_rows: Sequence[Any] | None,
    sleeper_roster: Mapping[str, Any] | None,
    players: Mapping[str, Mapping[str, Any]] | None,
    roster_fetched_at: datetime | str | None,
) -> dict[str, Any]:
    """Compare local roster rows with one already-authoritative Sleeper roster.

    The caller must identify the correct owner roster before calling this
    function. Missing roster identity, player mappings, or snapshot timestamp
    cause an UNKNOWN fail-closed result.
    """
    local_rows = list(local_rows or [])
    players = {str(key): value for key, value in (players or {}).items()}
    blockers: list[str] = []

    if not isinstance(sleeper_roster, Mapping):
        blockers.append("AUTHORITATIVE_SLEEPER_ROSTER_MISSING")
    if roster_fetched_at is None:
        blockers.append("ROSTER_SNAPSHOT_TIMESTAMP_MISSING")

    local_names = [_local_name(row) for row in local_rows]
    invalid_local_rows = [index for index, name in enumerate(local_names) if not name]
    if invalid_local_rows:
        blockers.append("INVALID_LOCAL_ROSTER_ROWS")

    valid_local_names = [name for name in local_names if name]
    local_keys = [normalize_player_name(name) for name in valid_local_names]
    duplicate_local_keys = sorted(
        key for key, count in Counter(local_keys).items() if key and count > 1
    )
    if duplicate_local_keys:
        blockers.append("DUPLICATE_LOCAL_PLAYERS")

    sleeper_ids = _sleeper_player_ids(sleeper_roster)
    sleeper_names: list[str] = []
    unmapped_player_ids: list[str] = []
    for player_id in sleeper_ids:
        player = players.get(player_id) or {}
        name = str(player.get("full_name") or "").strip()
        if not name:
            first = str(player.get("first_name") or "").strip()
            last = str(player.get("last_name") or "").strip()
            name = " ".join(part for part in (first, last) if part)
        if not name:
            unmapped_player_ids.append(player_id)
            continue
        sleeper_names.append(name)

    if unmapped_player_ids:
        blockers.append("UNMAPPED_SLEEPER_PLAYER_IDS")

    local_by_key = {normalize_player_name(name): name for name in valid_local_names}
    sleeper_by_key = {normalize_player_name(name): name for name in sleeper_names}
    local_key_set = {key for key in local_by_key if key}
    sleeper_key_set = {key for key in sleeper_by_key if key}

    matched_keys = sorted(local_key_set & sleeper_key_set)
    local_only_keys = sorted(local_key_set - sleeper_key_set)
    sleeper_only_keys = sorted(sleeper_key_set - local_key_set)

    hard_unknown = any(
        blocker in blockers
        for blocker in (
            "AUTHORITATIVE_SLEEPER_ROSTER_MISSING",
            "ROSTER_SNAPSHOT_TIMESTAMP_MISSING",
            "INVALID_LOCAL_ROSTER_ROWS",
            "DUPLICATE_LOCAL_PLAYERS",
            "UNMAPPED_SLEEPER_PLAYER_IDS",
        )
    )
    if hard_unknown:
        status = STATUS_UNKNOWN
        allowed = False
    elif local_only_keys or sleeper_only_keys:
        status = STATUS_DIVERGENT
        allowed = False
    else:
        status = STATUS_MATCHED
        allowed = True

    return {
        "status": status,
        "allowed": allowed,
        "read_only": True,
        "roster_updated_at": roster_fetched_at,
        "local_count": len(valid_local_names),
        "sleeper_count": len(sleeper_ids),
        "matched_count": len(matched_keys),
        "matched": [local_by_key[key] for key in matched_keys],
        "local_only": [local_by_key[key] for key in local_only_keys],
        "sleeper_only": [sleeper_by_key[key] for key in sleeper_only_keys],
        "unmapped_player_ids": sorted(unmapped_player_ids),
        "invalid_local_row_indexes": invalid_local_rows,
        "duplicate_local_keys": duplicate_local_keys,
        "blockers": blockers,
    }
