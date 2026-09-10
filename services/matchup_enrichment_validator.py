"""Batch A.8 read-only matchup enrichment coverage validation.

The caller supplies already-enriched roster rows and verified freshness metadata.
This module does not fetch, infer, persist, or submit anything.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

STATUS_VERIFIED = "VERIFIED"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNKNOWN = "UNKNOWN"


def _name(row: Mapping[str, Any], index: int) -> str:
    return str(row.get("player") or row.get("player_name") or f"row:{index}").strip()


def _matchup_freshness(freshness_metadata: Mapping[str, Any] | None) -> Any:
    metadata = freshness_metadata or {}
    for field in ("matchup_updated_at", "matchup_sync_time"):
        if metadata.get(field) is not None:
            return metadata[field]
    return None


def validate_matchup_enrichment(
    roster: Sequence[Mapping[str, Any]] | None,
    freshness_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate supplied matchup coverage without inventing missing evidence.

    Bye-week rows do not require opponent, matchup rank, or modifier evidence.
    Non-bye rows require opponent, matchup rank, and an explicitly supplied
    matchup modifier. A verified timestamp is required for a VERIFIED result.
    """
    rows = [dict(row) for row in (roster or [])]
    timestamp = _matchup_freshness(freshness_metadata)
    blockers: set[str] = set()
    missing_opponent: list[str] = []
    missing_rank: list[str] = []
    missing_modifier: list[str] = []
    invalid_rows: list[int] = []
    covered_players: list[str] = []

    if not rows:
        blockers.add("MATCHUP_DATA_MISSING")
    if timestamp is None:
        blockers.add("MATCHUP_FRESHNESS_UNKNOWN")

    required_count = 0
    covered_count = 0
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            invalid_rows.append(index)
            blockers.add("MATCHUP_ROW_INVALID")
            continue
        player = _name(row, index)
        if row.get("is_bye"):
            covered_players.append(player)
            continue
        required_count += 1
        complete = True
        if not str(row.get("opponent") or "").strip():
            missing_opponent.append(player)
            blockers.add("OPPONENT_DATA_MISSING")
            complete = False
        if row.get("matchup_rank") is None:
            missing_rank.append(player)
            blockers.add("MATCHUP_RANK_MISSING")
            complete = False
        if row.get("matchup_modifier") is None:
            missing_modifier.append(player)
            blockers.add("MATCHUP_MODIFIER_MISSING")
            complete = False
        if complete:
            covered_count += 1
            covered_players.append(player)

    coverage_score = round(covered_count / required_count * 100) if required_count else (100 if rows else 0)
    structural = {"MATCHUP_DATA_MISSING", "MATCHUP_ROW_INVALID", "MATCHUP_FRESHNESS_UNKNOWN"}
    if blockers & structural:
        status = STATUS_UNKNOWN
    elif blockers:
        status = STATUS_PARTIAL
    else:
        status = STATUS_VERIFIED

    confidence_score = coverage_score
    if blockers:
        confidence_score = min(confidence_score, 50)

    return {
        "status": status,
        "allowed": status == STATUS_VERIFIED,
        "read_only": True,
        "matchup_updated_at": timestamp,
        "player_count": len(rows),
        "required_matchup_players": required_count,
        "covered_matchup_players": covered_count,
        "coverage_score": coverage_score,
        "coverage_confidence": {
            "score": confidence_score,
            "label": "HIGH" if confidence_score >= 80 else "MEDIUM" if confidence_score >= 60 else "LOW",
        },
        "covered_players": sorted(covered_players),
        "missing_opponent_players": sorted(missing_opponent),
        "missing_rank_players": sorted(missing_rank),
        "missing_modifier_players": sorted(missing_modifier),
        "invalid_row_indexes": invalid_rows,
        "blockers": sorted(blockers),
    }
