"""Informational current-season matchup context, separate from authority."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SUPPORTED_POSITIONS = {"QB", "RB", "WR", "TE"}
SAMPLE_BLOCKER = "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED"


def build_preliminary_matchup_context(
    evidence: Mapping[str, Any] | None,
    *,
    roster: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Project fresh complete calculated evidence without decision fields."""
    base = {
        "state": "UNAVAILABLE",
        "authority": "INFORMATIONAL_ONLY",
        "matchups": [],
        "source": None,
        "retrieved_at": None,
        "freshness": "UNAVAILABLE",
        "completeness": "UNAVAILABLE",
        "sample_state": "SAMPLE_AUTHORITY_UNVERIFIED",
        "blocker": SAMPLE_BLOCKER,
        "decision_effect": "NONE",
    }
    if not evidence:
        return base
    provenance = evidence.get("provenance") or {}
    freshness = evidence.get("freshness") or {}
    completeness = evidence.get("completeness") or {}
    if str(provenance.get("source") or "").lower().startswith("csv:"):
        base.update(state="BLOCKED", blocker="HISTORICAL_MATCHUP_NOT_CURRENT")
        return base
    base.update({
        "source": provenance.get("source"),
        "retrieved_at": provenance.get("retrieved_at"),
        "freshness": freshness.get("status", "UNAVAILABLE"),
        "completeness": "COMPLETE" if completeness.get("complete") and completeness.get("defense_count") == completeness.get("required_defenses") == 32 else "INCOMPLETE",
    })
    if evidence.get("scoring_context", "FULL_PPR") != "FULL_PPR":
        base.update(state="BLOCKED", blocker="UNSUPPORTED_SCORING")
        return base
    if not provenance.get("source") or not provenance.get("retrieved_at"):
        base.update(state="UNAVAILABLE", blocker="MATCHUP_PROVENANCE_UNAVAILABLE")
        return base
    if freshness.get("status") != "FRESH":
        base.update(state="STALE" if freshness.get("status") in {"STALE", "EXPIRED"} else "BLOCKED", blocker=freshness.get("blocker") or "MATCHUP_FRESHNESS_NOT_FRESH")
        return base
    if base["completeness"] != "COMPLETE":
        base.update(state="BLOCKED", blocker="CURRENT_SEASON_DEFENSE_COMPLETENESS_REQUIRED")
        return base
    if evidence.get("blocker") not in {None, SAMPLE_BLOCKER}:
        base.update(state="BLOCKED", blocker=evidence.get("blocker"))
        return base
    selected = list(evidence.get("rows") or [])
    if roster is not None:
        wanted = {(str(player.get("position") or "").upper().replace("DST", "DEF"), str(player.get("opponent") or "").upper()) for player in roster if not player.get("is_bye")}
        selected = [row for row in selected if (str(row.get("position") or "").upper(), str(row.get("defense_team") or "").upper()) in wanted]
    for row in selected:
        position = str(row.get("position") or "").upper()
        if position not in SUPPORTED_POSITIONS:
            continue
        base["matchups"].append({
            "position": position,
            "defense_team": row.get("defense_team"),
            "fp_per_game_allowed": row.get("fp_per_game_allowed"),
            "completed_games": row.get("completed_games"),
            "defenses_represented": completeness.get("defense_count"),
            "required_defenses": completeness.get("required_defenses", 32),
            "scoring_context": "FULL_PPR",
            "unit": "fantasy_points_per_completed_game",
            "source": provenance.get("source"),
            "retrieved_at": provenance.get("retrieved_at"),
            "freshness": freshness.get("status"),
            "completeness": "COMPLETE",
            "sample_state": "SAMPLE_AUTHORITY_UNVERIFIED",
            "blocker": SAMPLE_BLOCKER,
            "decision_effect": "NONE",
        })
    if not base["matchups"]:
        base.update(state="UNAVAILABLE", blocker="MATCHUP_CONTEXT_NOT_AVAILABLE_FOR_ROSTER")
    else:
        base["state"] = "PRELIMINARY"
    return base
