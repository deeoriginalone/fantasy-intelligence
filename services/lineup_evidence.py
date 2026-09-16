"""Fail-closed projection, matchup, and combined lineup evidence contracts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from services.integrity.integrity_service import DEFAULT_FRESHNESS_LIMITS

SCHEMA_VERSION = "lineup-evidence.v1"
DECISION_EFFECT = "NONE"
VALID_FRESHNESS = {"FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED"}
VALID_COMPLETENESS = {"COMPLETE", "INCOMPLETE", "UNAVAILABLE"}
PROJECTION_WARNING_BLOCKERS = {
    "PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE",
    "PROJECTION_SOURCE_USE_UNVERIFIED",
    "PROJECTION_UNIT_UNVERIFIED",
    "PROJECTION_SOURCE_TIMESTAMP_UNAVAILABLE",
    "PROJECTION_FRESHNESS_THRESHOLD_UNVERIFIED",
    "PROJECTION_LINEAGE_VERSION_UNAVAILABLE",
}


def build_projection_evidence(player: Mapping[str, Any], *, season: Any, week: Any, now: Any = None) -> dict[str, Any]:
    value = player.get("projection")
    source = player.get("projection_source")
    retrieved_at = player.get("projection_retrieved_at")
    identity = _identity(player)
    blockers = []
    if not identity:
        blockers.append("PROJECTION_PLAYER_IDENTITY_UNAVAILABLE")
    if season is None:
        blockers.append("PROJECTION_SEASON_UNAVAILABLE")
    if week is None:
        blockers.append("PROJECTION_WEEK_UNAVAILABLE")
    if value is None:
        blockers.append("PROJECTION_VALUE_UNAVAILABLE")
    if not source or source == "Unavailable":
        blockers.append("PROJECTION_SOURCE_UNAVAILABLE")
    if not retrieved_at:
        blockers.append("PROJECTION_RETRIEVAL_TIME_UNAVAILABLE")
    if source != "automated:projection":
        blockers.append("PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE")
    freshness_state = _freshness(retrieved_at, now, "projection")
    if freshness_state == "STALE":
        blockers.append("PROJECTION_DATA_STALE")
    elif freshness_state == "UNAVAILABLE":
        blockers.append("PROJECTION_FRESHNESS_UNAVAILABLE")
    return _domain(
        domain="projection", season=season, week=week, identity=identity,
        value=value, source=source, retrieved_at=retrieved_at,
        freshness_state=freshness_state, completeness_state="COMPLETE" if not blockers else "INCOMPLETE",
        blockers=blockers, lineage=player.get("projection_lineage"),
        extra={
            "projection_unit": "season_points", "scoring_context": "FULL_PPR",
            "projection_consumable": value is not None and bool(identity) and bool(retrieved_at),
        },
    )


def build_matchup_evidence(player: Mapping[str, Any], *, season: Any, week: Any, now: Any = None) -> dict[str, Any]:
    opponent = player.get("opponent")
    source = player.get("matchup_source")
    retrieved_at = player.get("matchup_retrieved_at")
    identity = _identity(player)
    blockers = []
    if not identity:
        blockers.append("MATCHUP_PLAYER_IDENTITY_UNAVAILABLE")
    if not opponent:
        blockers.append("MATCHUP_OPPONENT_IDENTITY_UNAVAILABLE")
    if season is None:
        blockers.append("MATCHUP_SEASON_UNAVAILABLE")
    if week is None:
        blockers.append("MATCHUP_WEEK_UNAVAILABLE")
    if not source or source == "Unavailable":
        blockers.append("MATCHUP_SOURCE_UNAVAILABLE")
    if not retrieved_at:
        blockers.append("MATCHUP_RETRIEVAL_TIME_UNAVAILABLE")
    if not source or not source.startswith("automated:nflverse"):
        blockers.append("MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE")
    sample_threshold_id = player.get("matchup_sample_threshold_id")
    population = player.get("matchup_population")
    directionality = player.get("matchup_directionality")
    if not sample_threshold_id:
        blockers.append("MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED")
    if not population:
        blockers.append("MATCHUP_POPULATION_UNVERIFIED")
    if not directionality:
        blockers.append("MATCHUP_DIRECTIONALITY_UNVERIFIED")
    freshness_state = _freshness(retrieved_at, now, "matchup")
    if freshness_state == "STALE":
        blockers.append("MATCHUP_DATA_STALE")
    elif freshness_state == "UNAVAILABLE":
        blockers.append("MATCHUP_FRESHNESS_UNAVAILABLE")
    return _domain(
        domain="matchup", season=season, week=week, identity=identity,
        value=player.get("matchup_rank"), source=source, retrieved_at=retrieved_at,
        freshness_state=freshness_state, completeness_state="COMPLETE" if not blockers else "INCOMPLETE",
        blockers=blockers, lineage=player.get("matchup_publication_lineage") or player.get("matchup_lineage"),
        extra={"opponent_identity": opponent, "position": player.get("position"), "scoring_context": "FULL_PPR", "rank_directionality": directionality, "comparison_population": population, "sample_size": player.get("matchup_sample_size"), "sample_threshold_id": sample_threshold_id, "version": player.get("matchup_version"), "checksum": player.get("matchup_checksum"), "artifact_id": player.get("matchup_artifact_id"), "release_id": player.get("matchup_release_id"), "source_recorded_at": player.get("matchup_source_recorded_at")},
    )


def build_lineup_evidence(projection: Mapping[str, Any], matchup: Mapping[str, Any]) -> dict[str, Any]:
    projection = deepcopy(dict(projection))
    matchup = deepcopy(dict(matchup))
    blockers = list(dict.fromkeys([*(projection.get("blockers") or []), *(matchup.get("blockers") or [])]))
    freshness = _combined_freshness(projection.get("freshness_state"), matchup.get("freshness_state"))
    completeness = "COMPLETE" if projection.get("completeness_state") == matchup.get("completeness_state") == "COMPLETE" and not blockers else "INCOMPLETE"
    state = "AVAILABLE" if not blockers and freshness in {"FRESH", "AGING"} and completeness == "COMPLETE" else ("STALE" if freshness == "STALE" else "BLOCKED" if blockers else "UNAVAILABLE")
    return {
        "state": state,
        "authoritative": state == "AVAILABLE",
        "projection_consumable": bool(projection.get("projection_consumable")),
        "projection": projection,
        "matchup": matchup,
        "freshness_state": freshness,
        "completeness_state": completeness,
        "blockers": blockers,
        "lineage": {"projection": projection.get("lineage"), "matchup": matchup.get("lineage")},
        "schema_version": SCHEMA_VERSION,
        "decision_effect": DECISION_EFFECT,
    }


def _domain(*, domain: str, season: Any, week: Any, identity: Mapping[str, Any], value: Any, source: Any, retrieved_at: Any, freshness_state: str, completeness_state: str, blockers: list[str], lineage: Any, extra: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "domain": domain, "season": season, "week": week, "identity": identity,
        "value": value, "source": source or "UNVERIFIED", "source_authority": "automated" if source and str(source).startswith("automated:") else "UNVERIFIED",
        "source_recorded_at": None, "retrieved_at": retrieved_at, "imported_at": None,
        "age": None, "freshness_threshold_id": f"{domain}.freshness.v1", "freshness_state": freshness_state,
        "completeness_state": completeness_state, "blockers": list(dict.fromkeys(blockers)), "lineage": deepcopy(lineage),
        "schema_version": SCHEMA_VERSION, "fallback_used": None, "decision_effect": DECISION_EFFECT,
        "authoritative": not blockers and freshness_state in {"FRESH", "AGING"} and completeness_state == "COMPLETE",
        **dict(extra),
    }


def _identity(player: Mapping[str, Any]) -> dict[str, Any]:
    return {key: player[key] for key in ("source_player_id", "local_player_id") if player.get(key) is not None}


def _freshness(retrieved_at: Any, now: Any, domain: str) -> str:
    if not retrieved_at:
        return "UNAVAILABLE"
    from services.integrity.integrity_service import calculate_freshness
    if isinstance(now, str):
        now = __import__("datetime").datetime.fromisoformat(now.replace("Z", "+00:00"))
    result = calculate_freshness({f"{domain}_retrieved_at": retrieved_at, f"{domain}_source": "supplied"}, domain, now=now, max_age_seconds=DEFAULT_FRESHNESS_LIMITS[domain])
    if result["status"] in {"STALE", "EXPIRED"}:
        return "STALE"
    return result["status"] if result["status"] in {"FRESH", "AGING"} else "UNAVAILABLE"


def _combined_freshness(projection: Any, matchup: Any) -> str:
    states = {projection, matchup}
    if "STALE" in states:
        return "STALE"
    if "UNAVAILABLE" in states:
        return "UNAVAILABLE"
    if "BLOCKED" in states:
        return "BLOCKED"
    return "AGING" if "AGING" in states else "FRESH"
