"""Fail-closed validation for nflverse weekly statistics."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.defense_matchup_calculation import POSITIONS


def validate_nflverse_weekly_stats(rows: Sequence[Mapping[str, Any]], *, season: int, scoring: str = "full_ppr") -> dict[str, Any]:
    blockers = []
    if scoring.casefold() != "full_ppr":
        blockers.append("UNSUPPORTED_SCORING")
    invalid = []
    for index, row in enumerate(rows):
        position = str(row.get("position") or row.get("position_group") or "").upper().replace("DST", "DEF")
        if position in POSITIONS and not (row.get("defense_team") or row.get("opponent_team") or row.get("defteam")):
            invalid.append(index)
    if invalid:
        blockers.append("DEFENSE_IDENTITY_MISSING")
    return {"valid": not blockers, "season": season, "scoring": scoring, "accepted_rows": len(rows) - len(invalid), "invalid_row_indexes": invalid, "blockers": blockers}